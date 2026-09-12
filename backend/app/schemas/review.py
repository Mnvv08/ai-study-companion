"""
app/schemas/review.py
─────────────────────
Response models for the spaced-repetition endpoints.
"""

from datetime import datetime

from pydantic import BaseModel, Field


class TopicScheduleItem(BaseModel):
    """One topic's spaced-repetition standing."""

    topic: str = Field(..., description="Topic tag, matching Question.topic_tag.")
    due_at: datetime = Field(..., description="When this topic next needs review.")
    days_overdue: int = Field(
        ..., description="Days past due. 0 if not yet due."
    )
    interval_days: int = Field(
        ..., description="Current gap between reviews, in days."
    )
    repetitions: int = Field(
        ..., description="Consecutive passes. Resets to 0 on a failure."
    )
    ease_factor: float = Field(
        ..., description="How fast the interval grows. Starts 2.5, floors 1.3."
    )
    lapses: int = Field(
        ..., description="Times this topic was failed after previously passing."
    )
    total_reviews: int = Field(..., description="All reviews ever, passed or failed.")
    mastery: str = Field(
        ..., description="Plain-language standing: learning, shaky, improving, solid."
    )

    model_config = {"from_attributes": True}


class DueReviewsResponse(BaseModel):
    """Topics due for review right now."""

    due_count: int = Field(..., description="How many topics are returned.")
    total_tracked: int = Field(
        ..., description="All topics being tracked, due or not."
    )
    items: list[TopicScheduleItem] = Field(
        default_factory=list, description="Most overdue first."
    )
