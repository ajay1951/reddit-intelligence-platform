from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class SubredditSchema(BaseModel):
    id: int
    name: str
    url: str | None
    created_at: datetime | None
    post_count: int

    model_config = {
        "from_attributes": True,
    }
