import asyncio
from datetime import datetime, timezone
import hashlib
import os
import re
from typing import Any, Callable, Optional
import uuid

from apify_client import ApifyClientAsync
import redis.asyncio as redis
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
import structlog

from backend.analytics.extraction_engine import extract_technologies
from backend.analytics.sentiment_engine import analyze_sentiment
from backend.config import settings
import backend.database.connection as default_db
from backend.etl.cleaning import clean_text, normalize_author, normalize_url
from backend.models.models import Comment, Post, Subreddit

logger = structlog.get_logger(__name__)


def _make_comment_id(external_id: str | None, author: str | None, content: str) -> int:
    """Generate a stable 63-bit integer hash within PostgreSQL BigInteger positive range."""
    seed = f"{external_id or ''}:{author or ''}:{content[:100]}"
    hash_hex = hashlib.sha256(seed.encode("utf-8")).hexdigest()
    # 63-bit signed integer max is 9223372036854775807 (2**63 - 1)
    val = int(hash_hex[:15], 16)
    return max(1, val % (2**63 - 1))


def parse_iso_datetime(date_str: str | None) -> tuple[Optional[datetime], bool]:
    """
    Parse an ISO timestamp and normalize to UTC.
    Returns (normalized_datetime, is_fallback).
    """
    if not date_str:
        return datetime.now(timezone.utc), True

    try:
        ts_clean = date_str.replace("Z", "+00:00")
        dt = datetime.fromisoformat(ts_clean)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        else:
            dt = dt.astimezone(timezone.utc)
        return dt, False
    except Exception:
        return datetime.now(timezone.utc), True


async def run_subreddit_etl(
    subreddit_name: str,
    post_limit: int = 25,
    comment_limit: int = 5,
    start_date: str | None = None,
    end_date: str | None = None,
    session_maker: Optional[Callable[[], AsyncSession]] = None,
    provider: str | None = None,
):
    # 1. Strict date parsing & validation
    dt_start: Optional[datetime] = None
    if start_date:
        try:
            dt_start = datetime.strptime(start_date.strip(), "%Y-%m-%d").replace(tzinfo=timezone.utc)
        except ValueError as e:
            raise ValueError(f"Invalid start_date format '{start_date}'. Expected YYYY-MM-DD.") from e

    dt_end: Optional[datetime] = None
    if end_date:
        try:
            dt_end = datetime.strptime(end_date.strip(), "%Y-%m-%d").replace(
                hour=23, minute=59, second=59, microsecond=999999, tzinfo=timezone.utc
            )
        except ValueError as e:
            raise ValueError(f"Invalid end_date format '{end_date}'. Expected YYYY-MM-DD.") from e

    if dt_start and dt_end and dt_start > dt_end:
        raise ValueError(f"start_date ({start_date}) cannot be after end_date ({end_date}).")

    chosen_provider = (provider or settings.ingestion_provider or "auto").lower()
    session_factory = session_maker or default_db.AsyncSessionLocal

    # Direct execution of live Reddit RSS provider
    if chosen_provider in ("reddit_live", "live"):
        from backend.etl.reddit_public_provider import ingest_from_reddit_live
        async with session_factory() as session:
            return await ingest_from_reddit_live(
                subreddit_name=subreddit_name,
                post_limit=post_limit,
                comment_limit=comment_limit,
                session=session,
            )

    # Direct execution of Hugging Face provider
    if chosen_provider == "huggingface":
        from backend.etl.hf_provider import ingest_from_huggingface
        async with session_factory() as session:
            return await ingest_from_huggingface(
                subreddit_name=subreddit_name,
                post_limit=post_limit,
                comment_limit=comment_limit,
                start_date=start_date,
                end_date=end_date,
                session=session,
            )


    # Check Apify credentials if Apify or Auto is requested
    if not settings.apify_api_token:
        if chosen_provider == "apify":
            raise ValueError("APIFY_API_TOKEN is not set in the environment.")
        # Auto-fallback to Hugging Face when Apify token is missing
        logger.info("APIFY_API_TOKEN not set; defaulting to Hugging Face provider", subreddit=subreddit_name)
        from backend.etl.hf_provider import ingest_from_huggingface
        async with session_factory() as session:
            return await ingest_from_huggingface(
                subreddit_name=subreddit_name,
                post_limit=post_limit,
                comment_limit=comment_limit,
                start_date=start_date,
                end_date=end_date,
                session=session,
            )

    logger.info("Starting ETL via Apify", subreddit=subreddit_name)
    client = ApifyClientAsync(settings.apify_api_token)

    async with session_factory() as session:
        try:
            # 2. Ensure subreddit exists
            query = select(Subreddit).where(Subreddit.name == subreddit_name)
            result = await session.execute(query)
            subreddit = result.scalar_one_or_none()

            if not subreddit:
                subreddit = Subreddit(
                    name=subreddit_name,
                    url=f"https://reddit.com/r/{subreddit_name}",
                    created_at=datetime.now(timezone.utc).replace(tzinfo=None),
                )
                session.add(subreddit)
                await session.flush()

            posts_fetched = 0
            comments_fetched = 0
            new_post_ids: list[int] = []
            new_comment_ids: list[int] = []
            after_token = None

            while posts_fetched < post_limit:
                url = f"https://www.reddit.com/r/{subreddit_name}/new/"
                if after_token:
                    url += f"?after={after_token}"

                total_items_needed = (post_limit - posts_fetched) * (comment_limit + 1)
                run_input = {
                    "startUrls": [{"url": url}],
                    "maxItems": min(total_items_needed, 500),
                    "skipComments": comment_limit == 0,
                    "maxComments": comment_limit,
                    "proxyConfiguration": {"useApifyProxy": True},
                    "maxConcurrency": 1,
                    "maxRequestRetries": 10,
                    "pageLoadTimeoutSecs": 60,
                }
                if dt_start:
                    run_input["oldestPostDate"] = dt_start.strftime("%Y-%m-%d")

                logger.info("Calling Apify actor", subreddit=subreddit_name, input=run_input)
                run = await client.actor("trudax/reddit-scraper-lite").call(run_input=run_input)

                logger.info("Apify actor finished", run_id=run.id)
                dataset_client = client.dataset(run.default_dataset_id)
                dataset_items = await dataset_client.list_items()

                raw_items = dataset_items.items or []
                posts_data = [item for item in raw_items if item.get("dataType") != "comment"]
                comments_data = [item for item in raw_items if item.get("dataType") == "comment"]

                if not posts_data:
                    break

                new_posts_in_batch = 0
                post_id_map: dict[str, int] = {}

                for pdata in posts_data:
                    raw_url = pdata.get("url", "")
                    post_url = normalize_url(raw_url)
                    if not post_url:
                        logger.warning("Quarantining post record: missing or invalid URL", record_id=pdata.get("id"))
                        continue

                    created_at, is_fallback = parse_iso_datetime(pdata.get("createdAt"))
                    if is_fallback:
                        logger.info("Post timestamp fallback applied", post_url=post_url)

                    if dt_end and created_at > dt_end:
                        logger.debug("Skipping item: created_at > dt_end", created_at=created_at, dt_end=dt_end)
                        continue

                    # Idempotent post query
                    post_query = select(Post).where(Post.url == post_url)
                    post_res = await session.execute(post_query)
                    existing_post = post_res.scalar_one_or_none()

                    if not existing_post:
                        content = pdata.get("text", pdata.get("body", "")) or ""
                        if not content and "title" in pdata:
                            content = pdata["title"]

                        sentiment = analyze_sentiment(content)
                        techs = extract_technologies(content)

                        raw_author = pdata.get("author", pdata.get("username", pdata.get("parsedAuthor", "[deleted]")))
                        author = normalize_author(raw_author) or "[deleted]"

                        post = Post(
                            title=clean_text(pdata.get("title", "")) or "Untitled",
                            author=author,
                            subreddit_id=subreddit.id,
                            score=int(pdata.get("upvotes", pdata.get("score", 0)) or 0),
                            comments_count=int(pdata.get("numComments", 0) or 0),
                            url=post_url,
                            content=clean_text(content) or "",
                            created_at=created_at.replace(tzinfo=None),
                            scraped_at=datetime.now(timezone.utc).replace(tzinfo=None),
                            sentiment_score=sentiment["sentiment_score"],
                            sentiment_label=sentiment["sentiment_label"],
                            technologies=techs,
                        )
                        session.add(post)
                        await session.flush()
                        new_posts_in_batch += 1
                        new_post_ids.append(post.id)
                    else:
                        post = existing_post

                    parsed_id = pdata.get("parsedId") or pdata.get("id")
                    if parsed_id:
                        post_id_map[str(parsed_id)] = post.id

                    posts_fetched += 1

                # Ingest comments idempotently
                for cdata in comments_data[: post_limit * comment_limit]:
                    parsed_post_id = cdata.get("postId")
                    if not parsed_post_id:
                        continue

                    db_post_id = post_id_map.get(str(parsed_post_id))
                    if not db_post_id:
                        post_query = select(Post.id).where(Post.url.like(f"%{parsed_post_id}%"))
                        post_res = await session.execute(post_query)
                        db_post_id = post_res.scalar_one_or_none()

                    if not db_post_id:
                        continue

                    body = clean_text(cdata.get("text", cdata.get("body", "")))
                    if not body:
                        continue

                    c_created_at, _ = parse_iso_datetime(cdata.get("createdAt"))
                    raw_c_author = cdata.get("username", cdata.get("author", "[deleted]"))
                    c_author = normalize_author(raw_c_author) or "[deleted]"

                    comment_stable_id = _make_comment_id(cdata.get("id"), c_author, body)

                    # Deduplication check for comment
                    existing_comment_res = await session.execute(
                        select(Comment.id).where(
                            (Comment.id == comment_stable_id) |
                            ((Comment.post_id == db_post_id) & (Comment.author == c_author) & (Comment.content == body))
                        )
                    )
                    if existing_comment_res.scalar_one_or_none():
                        continue

                    sentiment = analyze_sentiment(body)
                    techs = extract_technologies(body)

                    comment = Comment(
                        id=comment_stable_id,
                        post_id=db_post_id,
                        author=c_author,
                        content=body,
                        score=int(cdata.get("upvotes", cdata.get("score", 0)) or 0),
                        created_at=c_created_at.replace(tzinfo=None),
                        sentiment_score=sentiment["sentiment_score"],
                        sentiment_label=sentiment["sentiment_label"],
                        technologies=techs,
                    )
                    session.add(comment)
                    await session.flush()
                    new_comment_ids.append(comment.id)
                    comments_fetched += 1

                if posts_data:
                    last_post = posts_data[-1]
                    if last_post.get("parsedId"):
                        after_token = f"t3_{last_post['parsedId']}"

                if new_posts_in_batch == 0:
                    logger.info("All fetched posts were duplicates or no new posts, ending loop.")
                    break

            await session.commit()

            # Incremental vector indexing of newly ingested posts and comments
            if new_post_ids or new_comment_ids:
                try:
                    from backend.services.semantic_service import SemanticService
                    semantic_service = SemanticService()
                    indexed_count = await semantic_service.index_posts_and_comments_batch(
                        session, post_ids=new_post_ids, comment_ids=new_comment_ids
                    )
                    logger.info("Incrementally indexed newly scraped items to vector database", count=indexed_count)
                except Exception as e:
                    logger.error("Incremental vector indexing failed", error=str(e))

            # Invalidate deep research cache safely without blocking Redis keys()
            try:
                redis_url = os.getenv("REDIS_URL", "redis://redis:6379/0")
                r = redis.from_url(redis_url, decode_responses=True)
                async for key in r.scan_iter("deep_research:*"):
                    await r.delete(key)
            except Exception as e:
                logger.error("Failed to invalidate cache", error=str(e))

            return {
                "status": "success",
                "subreddit": subreddit_name,
                "posts_scraped": posts_fetched,
                "comments_scraped": comments_fetched,
            }
        except Exception as e:
            await session.rollback()
            error_str = str(e)
            # If Apify encounters monthly usage hard limit, 403 Forbidden, or actor error, auto-fallback to Hugging Face
            if any(term in error_str.lower() for term in ("limit exceeded", "forbidden", "403", "usage limit", "rate limit")):
                logger.warning(
                    "Apify monthly quota exceeded or forbidden; automatically falling back to Hugging Face Parquet stream",
                    subreddit=subreddit_name,
                    error=error_str,
                )
                from backend.etl.hf_provider import ingest_from_huggingface
                return await ingest_from_huggingface(
                    subreddit_name=subreddit_name,
                    post_limit=post_limit,
                    comment_limit=comment_limit,
                    start_date=start_date,
                    end_date=end_date,
                    session=session,
                )
            logger.exception("Apify ETL failed", error=error_str)
            raise e


async def run_batch_etl(
    subreddits: list[str],
    post_limit: int = 25,
    comment_limit: int = 5,
    concurrency: int = 1,
    start_date: str | None = None,
    end_date: str | None = None,
    session_maker: Optional[Callable[[], AsyncSession]] = None,
    provider: str | None = None,
):
    logger.info("Starting background celery batch scrape task", subreddits=subreddits, provider=provider)

    tasks = []
    for sub in subreddits:
        tasks.append(
            run_subreddit_etl(
                sub,
                post_limit=post_limit,
                comment_limit=comment_limit,
                start_date=start_date,
                end_date=end_date,
                session_maker=session_maker,
                provider=provider,
            )
        )

    results = await asyncio.gather(*tasks, return_exceptions=True)
    return {
        "status": "batch_complete",
        "results": [
            r if isinstance(r, dict) else {"status": "error", "error": str(r)}
            for r in results
        ],
    }


