from __future__ import annotations

from .comments import router as comments_router
from .insights import router as insights_router
from .posts import router as posts_router
from .search import router as search_router
from .subreddits import router as subreddits_router
from .deep_research import router as deep_research_router

__all__ = [
    "comments_router",
    "insights_router",
    "posts_router",
    "search_router",
    "subreddits_router",
    "deep_research_router",
]
