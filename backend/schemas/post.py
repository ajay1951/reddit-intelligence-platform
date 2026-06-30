from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class PostSchema(BaseModel):
    id: int
    title: str
    author: str | None
    subreddit: str
    score: int
    comments_count: int
    url: str
    content: str | None
    created_at: datetime | None
    scraped_at: datetime | None

    model_config = {
        "from_attributes": True,
    }
