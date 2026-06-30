import asyncio
import structlog

from backend.celery_app import celery_app
from backend.etl.pipeline import run_batch_etl, run_subreddit_etl

logger = structlog.get_logger(__name__)

@celery_app.task(name="backend.etl.tasks.run_subreddit_scrape_task")
def run_subreddit_scrape_task(subreddit_name: str, post_limit: int = 25, comment_limit: int = 5):
    logger.info("Starting background celery scrape task", subreddit=subreddit_name)
    try:
        # Run the async pipeline inside a synchronous Celery task
        result = asyncio.run(run_subreddit_etl(subreddit_name, post_limit, comment_limit))
        logger.info("Completed celery scrape task", subreddit=subreddit_name, result=result)
        return result
    except Exception as e:
        logger.exception("Celery scrape task failed", subreddit=subreddit_name, error=str(e))
        raise

@celery_app.task(name="backend.etl.tasks.run_batch_scrape_task")
def run_batch_scrape_task(subreddits: list[str], post_limit: int = 25, comment_limit: int = 5, concurrency: int = 3):
    logger.info("Starting background celery batch scrape task", subreddits=subreddits)
    try:
        result = asyncio.run(run_batch_etl(subreddits, post_limit, comment_limit, concurrency))
        logger.info("Completed celery batch scrape task", result=result)
        return result
    except Exception as e:
        logger.exception("Celery batch scrape task failed", subreddits=subreddits, error=str(e))
        raise
