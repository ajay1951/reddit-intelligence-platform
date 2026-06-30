from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class CommentSchema(BaseModel):
    id: int
    post_id: int
    post_url: str | None
    subreddit: str | None
    author: str | None
    content: str
    score: int
    created_at: datetime | None

    model_config = {
        "from_attributes": True,
    }
