from __future__ import annotations

import re
from collections import Counter

from sqlalchemy.ext.asyncio import AsyncSession

from backend.repositories.comment_repository import CommentRepository
from backend.repositories.post_repository import PostRepository
from backend.repositories.subreddit_repository import SubredditRepository
from backend.schemas.insight import KeywordTrend, SkillSchema, SubredditTrend, TrendResponse

SKILL_KEYWORDS = [
    "python",
    "fastapi",
    "sqlalchemy",
    "docker",
    "postgres",
    "aws",
    "gcp",
    "kubernetes",
    "pytest",
    "asyncio",
    "data",
    "api",
    "backend",
    "frontend",
    "ai",
    "ml",
    "cloud",
    "devops",
    "pandas",
    "numpy",
]


class InsightService:
    def __init__(
        self,
        post_repository: PostRepository | None = None,
        comment_repository: CommentRepository | None = None,
        subreddit_repository: SubredditRepository | None = None,
    ) -> None:
        self.post_repository = post_repository or PostRepository()
        self.comment_repository = comment_repository or CommentRepository()
        self.subreddit_repository = subreddit_repository or SubredditRepository()

    async def get_skills(self, session: AsyncSession, limit: int = 20) -> list[SkillSchema]:
        posts = await self.post_repository.list_posts(session, limit=200, offset=0)
        comments = await self.comment_repository.list_comments(session, limit=400, offset=0)

        counter = Counter()
        for post in posts:
            counter.update(self._extract_skill_counts(post.title))
            if post.content:
                counter.update(self._extract_skill_counts(post.content))

        for comment in comments:
            counter.update(self._extract_skill_counts(comment.content))

        return [
            SkillSchema(name=skill, count=count)
            for skill, count in counter.most_common(limit)
            if count > 0
        ]

    async def get_trends(self, session: AsyncSession, limit: int = 10) -> TrendResponse:
        subreddit_rows = await self.subreddit_repository.list_subreddits(session, limit=limit, offset=0)
        skill_rows = await self.get_skills(session, limit=limit)

        return TrendResponse(
            top_subreddits=[
                SubredditTrend(subreddit=subreddit.name, count=post_count)
                for subreddit, post_count in subreddit_rows
            ],
            top_keywords=[
                KeywordTrend(keyword=skill.name, count=skill.count)
                for skill in skill_rows
            ],
        )

    def _extract_skill_counts(self, text: str) -> Counter[str]:
        text_lower = text.lower()
        counter: Counter[str] = Counter()
        for keyword in SKILL_KEYWORDS:
            pattern = re.compile(rf"\b{re.escape(keyword)}\b")
            matches = pattern.findall(text_lower)
            if matches:
                counter[keyword] = len(matches)
        return counter
