from datetime import datetime, timezone

from fastapi import Query
from lnbits.helpers import urlsafe_short_hash
from pydantic import BaseModel, Field


class CreatePrSettings(BaseModel):
    cost: int = Field(default=0, ge=0)
    wallet: str | None = Field(default=None)
    name: str | None = Field(default=None)
    description: str | None = Field(default=None)
    user_id: str | None = Field(default=None)
    comment_word_limit: int = Field(default=0, ge=0)
    tags: list[str] = Field(default_factory=list)


class PRSettings(BaseModel):
    id: str = Field(default_factory=urlsafe_short_hash)
    user_id: str | None = None
    wallet: str
    cost: int
    name: str | None = None
    description: str | None = None
    comment_word_limit: int = 0
    tags: list[str] = Field(default_factory=list)


class Review(BaseModel):
    id: str = Field(default_factory=urlsafe_short_hash)
    settings_id: str
    name: str | None = Field(default=None)
    tag: str | None = Field(default=None)
    rating: int = Field(default=0, ge=0, le=1000)
    comment: str | None = Field(default=None)
    paid: bool = Field(default=False)
    payment_hash: str | None = Field(default=None)
    created_at: int = Field(
        default_factory=lambda: int(datetime.now(timezone.utc).timestamp())
    )


class PostReview(BaseModel):
    settings_id: str | None = Field(default=None)
    name: str | None = Query(None)
    tag: str | None = Query(None)
    rating: int = Query(..., ge=0, le=1000)
    comment: str | None = Query(None)


class KeysetPage(BaseModel):
    items: list[Review]
    next_cursor: int | None = None
    review_count: int = 0
    avg_rating: float = 0.0


class RatingStats(BaseModel):
    tag: str | None = None
    review_count: int = Field(0, ge=0)
    avg_rating: int
