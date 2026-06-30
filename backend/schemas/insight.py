from __future__ import annotations

from pydantic import BaseModel


class SkillSchema(BaseModel):
    name: str
    count: int


class KeywordTrend(BaseModel):
    keyword: str
    count: int


class SubredditTrend(BaseModel):
    subreddit: str
    count: int


class TrendResponse(BaseModel):
    top_subreddits: list[SubredditTrend]
    top_keywords: list[KeywordTrend]
