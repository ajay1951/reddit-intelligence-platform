import asyncio
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
import structlog
import uuid
import redis.asyncio as redis
import os
from apify_client import ApifyClientAsync

from backend.database.connection import get_session, AsyncSessionLocal
from backend.models.models import Subreddit, Post, Comment
from backend.analytics.sentiment_engine import analyze_sentiment
from backend.analytics.extraction_engine import extract_technologies
from backend.config import settings

logger = structlog.get_logger(__name__)

async def run_subreddit_etl(subreddit_name: str, post_limit: int = 25, comment_limit: int = 5, start_date: str | None = None, end_date: str | None = None):
    logger.info("Starting ETL via Apify", subreddit=subreddit_name)
    
    if not settings.apify_api_token:
        raise ValueError("APIFY_API_TOKEN is not set in the environment.")
        
    client = ApifyClientAsync(settings.apify_api_token)
    
    import backend.database.connection as db
    async with db.AsyncSessionLocal() as session:
        try:
            # 1. Ensure subreddit exists
            query = select(Subreddit).where(Subreddit.name == subreddit_name)
            result = await session.execute(query)
            subreddit = result.scalar_one_or_none()
            
            if not subreddit:
                subreddit = Subreddit(name=subreddit_name, url=f"https://reddit.com/r/{subreddit_name}")
                session.add(subreddit)
                await session.flush()
                
            # Date boundaries
            dt_start = None
            if start_date:
                try:
                    dt_start = datetime.strptime(start_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
                except Exception:
                    pass
            dt_end = None
            if end_date:
                try:
                    dt_end = datetime.strptime(end_date, "%Y-%m-%d").replace(hour=23, minute=59, second=59, tzinfo=timezone.utc)
                except Exception:
                    pass
            
            posts_fetched = 0
            comments_fetched = 0
            after_token = None
            
            while posts_fetched < post_limit:
                url = f"https://www.reddit.com/r/{subreddit_name}/new/"
                if after_token:
                    url += f"?after={after_token}"
                    
                # Prepare Apify Inputs
                # maxItems must include enough room for both posts and their comments!
                total_items_needed = (post_limit - posts_fetched) * (comment_limit + 1)
                run_input = {
                    "startUrls": [{"url": url}],
                    "maxItems": min(total_items_needed, 1000), # cap at 1000 items per loop iteration
                    "skipComments": comment_limit == 0,
                    "maxComments": comment_limit,
                    "proxyConfiguration": {"useApifyProxy": True},
                    "maxConcurrency": 1,
                    "maxRequestRetries": 15,
                    "pageLoadTimeoutSecs": 60
                }
                if dt_start:
                    run_input["oldestPostDate"] = dt_start.strftime("%Y-%m-%d")
                    
                logger.info("Calling Apify actor", subreddit=subreddit_name, input=run_input)
                run = await client.actor("trudax/reddit-scraper-lite").call(run_input=run_input)
                
                logger.info("Apify actor finished", run_id=run.id)
                dataset_client = client.dataset(run.default_dataset_id)
                dataset_items = await dataset_client.list_items()
                
                posts_data = [item for item in dataset_items.items if item.get("dataType") != "comment"]
                comments_data = [item for item in dataset_items.items if item.get("dataType") == "comment"]
                
                if not posts_data:
                    break
                    
                new_posts_in_batch = 0
                post_id_map = {}
                
                for pdata in posts_data:
                    post_url = pdata.get("url", "")
                    if not post_url: continue
                    
                    created_at = datetime.now(timezone.utc)
                    if pdata.get("createdAt"):
                        try:
                            ts_str = pdata["createdAt"].replace("Z", "+00:00")
                            created_at = datetime.fromisoformat(ts_str).astimezone(timezone.utc)
                        except Exception:
                            pass
                            
                    if dt_end and created_at > dt_end:
                        logger.info("Skipping item: > dt_end", created_at=created_at, dt_end=dt_end)
                        continue
                        
                    post_query = select(Post).where(Post.url == post_url)
                    post_res = await session.execute(post_query)
                    existing_post = post_res.scalar_one_or_none()
                    
                    if not existing_post:
                        content = pdata.get("text", pdata.get("body", ""))
                        if not content and "title" in pdata:
                            content = pdata["title"]
                            
                        sentiment = analyze_sentiment(content)
                        techs = extract_technologies(content)
                        
                        post = Post(
                            title=pdata.get("title", ""),
                            author=pdata.get("author", pdata.get("username", pdata.get("parsedAuthor", "[deleted]"))),
                            subreddit_id=subreddit.id,
                            score=pdata.get("upvotes", pdata.get("score", 0)),
                            comments_count=pdata.get("numComments", 0),
                            url=post_url,
                            content=content,
                            created_at=created_at.replace(tzinfo=None),
                            sentiment_score=sentiment["sentiment_score"],
                            sentiment_label=sentiment["sentiment_label"],
                            technologies=techs
                        )
                        session.add(post)
                        await session.flush()
                        new_posts_in_batch += 1
                    else:
                        post = existing_post
                        
                    if pdata.get("parsedId"):
                        post_id_map[pdata["parsedId"]] = post.id
                        
                    posts_fetched += 1
                    
                for cdata in comments_data[:post_limit * comment_limit]:
                    parsed_post_id = cdata.get("postId")
                    if not parsed_post_id: continue
                        
                    db_post_id = post_id_map.get(parsed_post_id)
                    if not db_post_id:
                        post_query = select(Post.id).where(Post.url.like(f"%{parsed_post_id}%"))
                        post_res = await session.execute(post_query)
                        db_post_id = post_res.scalar_one_or_none()
                        
                    if not db_post_id: continue
                        
                    body = cdata.get("text", cdata.get("body", ""))
                    if not body: continue
                    
                    sentiment = analyze_sentiment(body)
                    techs = extract_technologies(body)
                    
                    c_created_at = datetime.now(timezone.utc)
                    if cdata.get("createdAt"):
                        try:
                            c_ts_str = cdata["createdAt"].replace("Z", "+00:00")
                            c_created_at = datetime.fromisoformat(c_ts_str).astimezone(timezone.utc)
                        except Exception:
                            pass
                            
                    comment = Comment(
                        post_id=db_post_id,
                        author=cdata.get("username", cdata.get("author", "[deleted]")),
                        content=body,
                        score=cdata.get("upvotes", cdata.get("score", 0)),
                        created_at=c_created_at.replace(tzinfo=None),
                        sentiment_score=sentiment["sentiment_score"],
                        sentiment_label=sentiment["sentiment_label"],
                        technologies=techs
                    )
                    session.add(comment)
                    comments_fetched += 1
                    
                if posts_data:
                    last_post = posts_data[-1]
                    if last_post.get("parsedId"):
                        after_token = f"t3_{last_post['parsedId']}"
                        
                if new_posts_in_batch == 0:
                    logger.info("All fetched posts were duplicates or no new posts, ending loop.")
                    break
                    
            await session.commit()
            
            # Invalidate deep research cache
            try:
                redis_url = os.getenv("REDIS_URL", "redis://redis:6379/0")
                r = redis.from_url(redis_url, decode_responses=True)
                keys = await r.keys("deep_research:*")
                if keys:
                    await r.delete(*keys)
            except Exception as e:
                logger.error("Failed to invalidate cache", error=str(e))
                
            return {"status": "success", "subreddit": subreddit_name, "posts_scraped": posts_fetched, "comments_scraped": comments_fetched}
        except Exception as e:
            await session.rollback()
            logger.exception("Apify ETL failed", error=str(e))
            raise e

async def run_batch_etl(subreddits: list[str], post_limit: int = 25, comment_limit: int = 5, concurrency: int = 1, start_date: str | None = None, end_date: str | None = None):
    logger.info("Starting background celery batch scrape task", subreddits=subreddits)
    
    tasks = []
    for sub in subreddits:
        tasks.append(run_subreddit_etl(sub, post_limit, comment_limit, start_date, end_date))
        
    results = await asyncio.gather(*tasks, return_exceptions=True)
    return {"status": "batch_complete", "results": [str(r) for r in results]}
