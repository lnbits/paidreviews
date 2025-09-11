from datetime import datetime, timezone

from fastapi import Query
from pydantic import BaseModel, Field


class PRSettings(BaseModel):
    id: str | None = Field(default=None)
    cost: int = Field(default=0, ge=0)
    name: str | None = Field(default=None)
    description: str | None = Field(default=None)
    wallet: str | None = Field(default=None)
    user: str | None = Field(default=None)
    comment_word_limit: int = Field(default=0, ge=0)
    tags: list[str] = Field(default_factory=list)


class Review(BaseModel):
    id: str | None = Field(default=None)
    settings_id: str | None = Field(default=None)
    name: str | None = Field(default=None)
    tag: str | None = Field(default=None)
    rating: int = Field(default=0, ge=0, le=1000)
    comment: str | None = Field(default=None)
    paid: bool = Field(default=False)
    payment_hash: str | None = Field(default=None)


class PostReview(BaseModel):
    settings_id: str | None = Field(default=None)
    name: str | None = Query(None)
    tag: str | None = Query(None)
    rating: int = Query(..., ge=0, le=1000)
    comment: str | None = Query(None)


class ReturnedReview(BaseModel):
    id: str | None = Field(default=None)
    settings_id: str | None = Field(default=None)
    name: str | None = Field(default=None)
    tag: str | None = Field(default=None)
    rating: int = Field(default=0, ge=0, le=1000)
    comment: str | None = Field(default=None)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class KeysetPage(BaseModel):
    items: list[ReturnedReview]
    next_cursor: int | None = None
    review_count: int = 0
    avg_rating: float = 0.0


class RatingStats(BaseModel):
    review_count: int = Field(0, ge=0)
    avg_rating: float = 0.0
