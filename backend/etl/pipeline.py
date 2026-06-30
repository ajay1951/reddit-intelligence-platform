import asyncio
import httpx
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
import structlog
import uuid

from backend.database.connection import get_session
from backend.models.models import Subreddit, Post, Comment
from backend.analytics.sentiment_engine import analyze_sentiment
from backend.analytics.extraction_engine import extract_technologies

logger = structlog.get_logger(__name__)

async def fetch_reddit_json(url: str):
    async with httpx.AsyncClient() as client:
        # reddit strictly requires a unique user agent format
        headers = {"User-Agent": "windows:reddit-intelligence-app:v1.0.0 (by /u/developer)"}
        response = await client.get(url, headers=headers)
        response.raise_for_status()
        return response.json()

async def run_subreddit_etl(subreddit_name: str, post_limit: int = 25, comment_limit: int = 5):
    logger.info("Starting ETL", subreddit=subreddit_name)
    
    session_gen = get_session()
    session: AsyncSession = await anext(session_gen)
    
    try:
        # 1. Ensure subreddit exists
        query = select(Subreddit).where(Subreddit.name == subreddit_name)
        result = await session.execute(query)
        subreddit = result.scalar_one_or_none()
        
        if not subreddit:
            subreddit = Subreddit(name=subreddit_name, url=f"https://reddit.com/r/{subreddit_name}")
            session.add(subreddit)
            await session.flush()
        
        # 2. Loop to fetch posts with Pagination
        posts_fetched = 0
        after_token = None
        
        while posts_fetched < post_limit:
            batch_limit = min(100, post_limit - posts_fetched)
            url = f"https://www.reddit.com/r/{subreddit_name}/hot.json?limit={batch_limit}"
            if after_token:
                url += f"&after={after_token}"
                
            try:
                await asyncio.sleep(1.5) 
                posts_data = await fetch_reddit_json(url)
            except Exception as e:
                logger.error("Failed to fetch subreddit data", subreddit=subreddit_name, error=str(e))
                break

            children = posts_data.get("data", {}).get("children", [])
            if not children:
                break

            for post_item in children:
                pdata = post_item["data"]
                post_url = f"https://www.reddit.com{pdata['permalink']}"
                
                # Check if post exists
                post_query = select(Post).where(Post.url == post_url)
                post_res = await session.execute(post_query)
                existing_post = post_res.scalar_one_or_none()
                
                if not existing_post:
                    content = pdata.get("selftext", "")
                    sentiment = analyze_sentiment(content)
                    techs = extract_technologies(content)
                    
                    post = Post(
                        title=pdata.get("title", ""),
                        author=pdata.get("author", "[deleted]"),
                        subreddit_id=subreddit.id,
                        score=pdata.get("score", 0),
                        comments_count=pdata.get("num_comments", 0),
                        url=post_url,
                        content=content,
                        created_at=datetime.fromtimestamp(pdata.get("created_utc", 0), tz=timezone.utc).replace(tzinfo=None),
                        sentiment_score=sentiment["sentiment_score"],
                        sentiment_label=sentiment["sentiment_label"],
                        technologies=techs
                    )
                    session.add(post)
                    await session.flush()
                else:
                    post = existing_post
                    
                # 3. Fetch comments
                try:
                    await asyncio.sleep(1.5)
                    comments_data = await fetch_reddit_json(f"{post_url}.json?limit={comment_limit}")
                    if isinstance(comments_data, list) and len(comments_data) > 1:
                        for comment_item in comments_data[1].get("data", {}).get("children", [])[:comment_limit]:
                            cdata = comment_item["data"]
                            if "body" not in cdata: continue
                            
                            sentiment = analyze_sentiment(cdata["body"])
                            techs = extract_technologies(cdata["body"])
                            
                            comment = Comment(
                                post_id=post.id,
                                author=cdata.get("author", "[deleted]"),
                                content=cdata["body"],
                                score=cdata.get("score", 0),
                                created_at=datetime.fromtimestamp(cdata.get("created_utc", 0), tz=timezone.utc).replace(tzinfo=None),
                                sentiment_score=sentiment["sentiment_score"],
                                sentiment_label=sentiment["sentiment_label"],
                                technologies=techs
                            )
                            session.add(comment)
                except Exception as e:
                    logger.error("Failed fetching comments", url=post_url, error=str(e))
            
            posts_fetched += len(children)
            after_token = posts_data.get("data", {}).get("after")
            
            if not after_token:
                break
                
        await session.commit()
        return {"status": "success", "subreddit": subreddit_name, "posts_scraped": posts_fetched}
    except Exception as e:
        await session.rollback()
        raise e
    finally:
        await session.close()

async def run_batch_etl(subreddits: list[str], post_limit: int = 25, comment_limit: int = 5, concurrency: int = 3):
    sem = asyncio.Semaphore(concurrency)
    async def process(sub):
        async with sem:
            return await run_subreddit_etl(sub, post_limit, comment_limit)
    
    results = await asyncio.gather(*[process(sub) for sub in subreddits], return_exceptions=True)
    return {"status": "batch_complete", "results": [str(r) for r in results]}
