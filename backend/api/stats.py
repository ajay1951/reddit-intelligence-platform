from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from backend.database.connection import get_session

router = APIRouter()

@router.get("/ingestion")
async def get_ingestion_stats(session: AsyncSession = Depends(get_session)):
    posts_res = await session.execute(text("SELECT COUNT(*) FROM posts"))
    comments_res = await session.execute(text("SELECT COUNT(*) FROM comments"))
    subs_res = await session.execute(text("SELECT COUNT(DISTINCT subreddit_id) FROM posts"))
    
    return {
        "total_posts": posts_res.scalar() or 0,
        "total_comments": comments_res.scalar() or 0,
        "monitored_subreddits": subs_res.scalar() or 0
    }

@router.get("/subreddit_volume")
async def get_subreddit_volume(session: AsyncSession = Depends(get_session)):
    query = """
        SELECT s.name as subreddit, COUNT(p.id) as count 
        FROM posts p
        JOIN subreddits s ON p.subreddit_id = s.id
        GROUP BY s.name 
        ORDER BY count DESC 
        LIMIT 10
    """
    res = await session.execute(text(query))
    return [{"subreddit": row[0], "count": row[1]} for row in res.fetchall()]

@router.get("/recent_posts")
async def get_recent_posts(session: AsyncSession = Depends(get_session)):
    query = """
        SELECT p.title, s.name as subreddit, p.scraped_at as created_at, p.url 
        FROM posts p
        JOIN subreddits s ON p.subreddit_id = s.id
        ORDER BY p.scraped_at DESC NULLS LAST 
        LIMIT 10
    """
    res = await session.execute(text(query))
    return [
        {
            "title": row[0],
            "subreddit": row[1],
            "created_at": row[2].isoformat() if row[2] else None,
            "url": row[3]
        }
        for row in res.fetchall()
    ]

@router.get("/trends_over_time")
async def get_trends_over_time(session: AsyncSession = Depends(get_session)):
    query = """
        SELECT DATE(created_at) as date, COUNT(*) as count
        FROM posts
        WHERE created_at IS NOT NULL
        GROUP BY DATE(created_at)
        ORDER BY date ASC
        LIMIT 30
    """
    res = await session.execute(text(query))
    return [{"date": row[0].isoformat() if row[0] else "", "count": row[1]} for row in res.fetchall()]
