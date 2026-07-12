import asyncio
import structlog

from backend.celery_app import celery_app
from backend.etl.pipeline import run_batch_etl, run_subreddit_etl

logger = structlog.get_logger(__name__)

@celery_app.task(name="backend.etl.tasks.run_subreddit_scrape_task")
def run_subreddit_scrape_task(subreddit_name: str, post_limit: int = 25, comment_limit: int = 5, start_date: str | None = None, end_date: str | None = None):
    logger.info("Starting background celery scrape task", subreddit=subreddit_name)
    try:
        async def run_with_engine_reinit():
            import backend.database.connection as db
            from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
            from sqlalchemy.pool import AsyncAdaptedQueuePool
            
            db.engine = create_async_engine(
                db.DATABASE_URL, 
                echo=False, 
                future=True, 
                poolclass=AsyncAdaptedQueuePool,
                pool_size=20,
                max_overflow=10
            )
            db.AsyncSessionLocal = async_sessionmaker(bind=db.engine, class_=db.AsyncSession, expire_on_commit=False)
            return await run_subreddit_etl(subreddit_name, post_limit, comment_limit, start_date, end_date)
            
        # Run the async pipeline inside a synchronous Celery task
        result = asyncio.run(run_with_engine_reinit())
        logger.info("Completed celery scrape task", subreddit=subreddit_name, result=result)
        return result
    except Exception as e:
        logger.exception("Celery scrape task failed", subreddit=subreddit_name, error=str(e))
        raise

@celery_app.task(name="backend.etl.tasks.run_batch_scrape_task")
def run_batch_scrape_task(subreddits: list[str], post_limit: int = 25, comment_limit: int = 5, concurrency: int = 1, start_date: str | None = None, end_date: str | None = None):
    logger.info("Starting background celery batch scrape task", subreddits=subreddits)
    try:
        async def run_with_engine_reinit():
            import backend.database.connection as db
            from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
            from sqlalchemy.pool import AsyncAdaptedQueuePool
            
            db.engine = create_async_engine(
                db.DATABASE_URL, 
                echo=False, 
                future=True, 
                poolclass=AsyncAdaptedQueuePool,
                pool_size=20,
                max_overflow=10
            )
            db.AsyncSessionLocal = async_sessionmaker(bind=db.engine, class_=db.AsyncSession, expire_on_commit=False)
            return await run_batch_etl(subreddits, post_limit, comment_limit, concurrency, start_date, end_date)
            
        result = asyncio.run(run_with_engine_reinit())
        logger.info("Completed celery batch scrape task", result=result)
        return result
    except Exception as e:
        logger.exception("Celery batch scrape task failed", subreddits=subreddits, error=str(e))
        raise
