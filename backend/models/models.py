from __future__ import annotations

from datetime import datetime
from typing import List

from sqlalchemy import (
    BigInteger,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    Index,
)
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.orm import declarative_base


Base = declarative_base()


class Subreddit(Base):
    """Represents a subreddit (basic metadata)."""

    __tablename__ = "subreddits"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    url: Mapped[str] = mapped_column(String(1024), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    posts = relationship("Post", back_populates="subreddit", cascade="all, delete-orphan")


class Post(Base):
    """Post scraped from Reddit."""

    __tablename__ = "posts"
    __table_args__ = (
        UniqueConstraint("url", name="uq_posts_url"),
        Index("ix_post_technologies", "technologies", postgresql_using="gin"),
        Index("ix_post_sentiment", "sentiment_label"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(1024), nullable=False)
    author: Mapped[str] = mapped_column(String(255), nullable=True)
    subreddit_id: Mapped[int] = mapped_column(ForeignKey("subreddits.id"), nullable=False)
    score: Mapped[int] = mapped_column(Integer, default=0)
    comments_count: Mapped[int] = mapped_column(Integer, default=0)
    url: Mapped[str] = mapped_column(String(2048), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    scraped_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    sentiment_score: Mapped[float | None] = mapped_column(Float, default=0.0)
    sentiment_label: Mapped[str | None] = mapped_column(String(50), nullable=True)
    technologies: Mapped[list[str] | None] = mapped_column(ARRAY(String), default=list)

    subreddit = relationship("Subreddit", back_populates="posts")
    comments = relationship("Comment", back_populates="post", cascade="all, delete-orphan")


class Comment(Base):
    """Comment under a post."""

    __tablename__ = "comments"
    __table_args__ = (
        UniqueConstraint("id", name="uq_comments_id"),
        Index("ix_comment_technologies", "technologies", postgresql_using="gin"),
        Index("ix_comment_sentiment", "sentiment_label"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    post_id: Mapped[int] = mapped_column(ForeignKey("posts.id"), nullable=False)
    author: Mapped[str] = mapped_column(String(255), nullable=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    score: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)

    sentiment_score: Mapped[float | None] = mapped_column(Float, default=0.0)
    sentiment_label: Mapped[str | None] = mapped_column(String(50), nullable=True)
    technologies: Mapped[list[str] | None] = mapped_column(ARRAY(String), default=list)

    post = relationship("Post", back_populates="comments")
