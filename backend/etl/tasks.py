import asyncio
import structlog

from backend.celery_app import celery_app
from backend.etl.pipeline import run_batch_etl, run_subreddit_etl

logger = structlog.get_logger(__name__)


@celery_app.task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    acks_late=True,
    name="backend.etl.tasks.run_subreddit_scrape_task",
)
def run_subreddit_scrape_task(
    self,
    subreddit_name: str,
    post_limit: int = 25,
    comment_limit: int = 5,
    start_date: str | None = None,
    end_date: str | None = None,
    provider: str | None = None,
):
    logger.info(
        "Starting background celery scrape task",
        subreddit=subreddit_name,
        provider=provider,
        attempt=self.request.retries + 1,
    )
    try:
        async def run_scoped_etl():
            import backend.database.connection as db
            from sqlalchemy.ext.asyncio import async_sessionmaker

            task_engine = db.create_scoped_engine(pool_size=5, max_overflow=2)
            task_session_maker = async_sessionmaker(bind=task_engine, class_=db.AsyncSession, expire_on_commit=False)
            try:
                return await run_subreddit_etl(
                    subreddit_name,
                    post_limit=post_limit,
                    comment_limit=comment_limit,
                    start_date=start_date,
                    end_date=end_date,
                    session_maker=task_session_maker,
                    provider=provider,
                )
            finally:
                logger.info("Disposing Celery task async engine pool", subreddit=subreddit_name)
                await task_engine.dispose()

        result = asyncio.run(run_scoped_etl())
        logger.info("Completed celery scrape task", subreddit=subreddit_name, result=result)
        return result
    except Exception as e:
        logger.exception(
            "Celery scrape task encountered error",
            subreddit=subreddit_name,
            error=str(e),
            attempt=self.request.retries + 1,
        )
        if self.request.retries < self.max_retries:
            countdown = min(60 * (2 ** self.request.retries), 600)
            logger.info("Scheduling bounded retry for task", subreddit=subreddit_name, countdown=countdown)
            raise self.retry(exc=e, countdown=countdown)
        raise e


@celery_app.task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    acks_late=True,
    name="backend.etl.tasks.run_batch_scrape_task",
)
def run_batch_scrape_task(
    self,
    subreddits: list[str],
    post_limit: int = 25,
    comment_limit: int = 5,
    concurrency: int = 1,
    start_date: str | None = None,
    end_date: str | None = None,
    provider: str | None = None,
):
    logger.info(
        "Starting background celery batch scrape task",
        subreddits=subreddits,
        provider=provider,
        attempt=self.request.retries + 1,
    )
    try:
        async def run_scoped_batch():
            import backend.database.connection as db
            from sqlalchemy.ext.asyncio import async_sessionmaker

            task_engine = db.create_scoped_engine(pool_size=5, max_overflow=2)
            task_session_maker = async_sessionmaker(bind=task_engine, class_=db.AsyncSession, expire_on_commit=False)
            from datetime import datetime
            from backend.models.models import IngestionRun

            run_id = None
            try:
                async with task_session_maker() as audit_session:
                    run_record = IngestionRun(
                        job_id="24h_auto_scrape" if not start_date else "batch_custom_scrape",
                        status="running",
                        subreddits=subreddits,
                        provider_used=provider or "auto",
                        started_at=datetime.utcnow(),
                    )
                    audit_session.add(run_record)
                    await audit_session.commit()
                    await audit_session.refresh(run_record)
                    run_id = run_record.id
            except Exception as audit_err:
                logger.warning("Failed to initialize IngestionRun audit record", error=str(audit_err))

            try:
                batch_res = await run_batch_etl(
                    subreddits,
                    post_limit=post_limit,
                    comment_limit=comment_limit,
                    concurrency=concurrency,
                    start_date=start_date,
                    end_date=end_date,
                    session_maker=task_session_maker,
                    provider=provider,
                )

                if run_id:
                    total_posts = 0
                    total_comments = 0
                    for r in batch_res.get("results", []):
                        if isinstance(r, dict):
                            total_posts += r.get("posts_scraped", 0)
                            total_comments += r.get("comments_scraped", 0)
                    try:
                        async with task_session_maker() as audit_session:
                            run_to_update = await audit_session.get(IngestionRun, run_id)
                            if run_to_update:
                                run_to_update.status = "success"
                                run_to_update.posts_ingested = total_posts
                                run_to_update.comments_ingested = total_comments
                                run_to_update.completed_at = datetime.utcnow()
                                await audit_session.commit()
                    except Exception as audit_err:
                        logger.warning("Failed to update IngestionRun success record", error=str(audit_err))

                return batch_res
            except Exception as task_err:
                if run_id:
                    try:
                        async with task_session_maker() as audit_session:
                            run_to_update = await audit_session.get(IngestionRun, run_id)
                            if run_to_update:
                                run_to_update.status = "failed"
                                run_to_update.error_message = str(task_err)
                                run_to_update.completed_at = datetime.utcnow()
                                await audit_session.commit()
                    except Exception as audit_err:
                        logger.warning("Failed to update IngestionRun failure record", error=str(audit_err))
                raise task_err
            finally:
                logger.info("Disposing Celery batch task async engine pool", subreddits=subreddits)
                await task_engine.dispose()

        result = asyncio.run(run_scoped_batch())
        logger.info("Completed celery batch scrape task", result=result)
        return result
    except Exception as e:
        logger.exception(
            "Celery batch scrape task encountered error",
            subreddits=subreddits,
            error=str(e),
            attempt=self.request.retries + 1,
        )
        if self.request.retries < self.max_retries:
            countdown = min(60 * (2 ** self.request.retries), 600)
            logger.info("Scheduling bounded retry for batch task", countdown=countdown)
            raise self.retry(exc=e, countdown=countdown)
        raise e
