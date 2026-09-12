"""
app/api/v1/review.py
────────────────────
Spaced-repetition endpoints.

  GET /review/due       → what to study right now
  GET /review/schedule  → the full picture, including topics not yet due

The analytics endpoints answer "what am I weak at". These answer "what should
I do about it today", which is the question a student actually acts on.
"""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.security import get_current_user
from app.db.session import get_db
from app.models.review import TopicReview
from app.models.user import User
from app.schemas.review import DueReviewsResponse, TopicScheduleItem

router = APIRouter(prefix="/review", tags=["Review"])


def _as_utc(value: datetime) -> datetime:
    """
    Guarantee a timezone-aware UTC datetime.

    Columns are declared DateTime(timezone=True), but what comes back depends
    on the driver: Postgres returns aware values, SQLite returns naive ones
    because it has no native timestamp type. Subtracting a naive from an aware
    datetime raises TypeError, so anything that does date arithmetic on a
    stored value normalises first rather than trusting the backend.
    """
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


def _mastery_label(row: TopicReview) -> str:
    """
    A plain-language summary of where a topic stands.

    Derived from interval length rather than raw score, because in a spaced
    system the interval already encodes the history: a topic only reaches a
    three-week gap by being answered correctly several times running.
    """
    if row.repetitions == 0:
        return "learning"
    if row.interval_days < SECOND_INTERVAL_THRESHOLD:
        return "shaky"
    if row.interval_days < MATURE_THRESHOLD_DAYS:
        return "improving"
    return "solid"


SECOND_INTERVAL_THRESHOLD = 6
MATURE_THRESHOLD_DAYS = 21


@router.get("/due", response_model=DueReviewsResponse)
def get_due_reviews(
    limit: int = Query(20, ge=1, le=100, description="Maximum topics to return."),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Topics due for review now, most overdue first.

    Ordering by due date rather than by weakness is the point of a spaced
    system: a topic failed three weeks ago and never revisited is more urgent
    than one failed yesterday, even if yesterday's score was lower.
    """
    now = datetime.now(timezone.utc)

    rows = (
        db.query(TopicReview)
        .filter(TopicReview.user_id == current_user.id, TopicReview.due_at <= now)
        .order_by(TopicReview.due_at.asc())
        .limit(limit)
        .all()
    )

    total_tracked = (
        db.query(TopicReview).filter(TopicReview.user_id == current_user.id).count()
    )

    items = [
        TopicScheduleItem(
            topic=r.topic,
            due_at=r.due_at,
            days_overdue=max(0, (now - _as_utc(r.due_at)).days),
            interval_days=r.interval_days,
            repetitions=r.repetitions,
            ease_factor=r.ease_factor,
            lapses=r.lapses,
            total_reviews=r.total_reviews,
            mastery=_mastery_label(r),
        )
        for r in rows
    ]

    return DueReviewsResponse(
        due_count=len(items),
        total_tracked=total_tracked,
        items=items,
    )


@router.get("/schedule", response_model=list[TopicScheduleItem])
def get_full_schedule(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Every tracked topic with its next review date, soonest first.

    Includes topics that aren't due yet, so a student can see the shape of the
    week ahead rather than only today's pile.
    """
    now = datetime.now(timezone.utc)

    rows = (
        db.query(TopicReview)
        .filter(TopicReview.user_id == current_user.id)
        .order_by(TopicReview.due_at.asc())
        .all()
    )

    return [
        TopicScheduleItem(
            topic=r.topic,
            due_at=r.due_at,
            days_overdue=max(0, (now - _as_utc(r.due_at)).days),
            interval_days=r.interval_days,
            repetitions=r.repetitions,
            ease_factor=r.ease_factor,
            lapses=r.lapses,
            total_reviews=r.total_reviews,
            mastery=_mastery_label(r),
        )
        for r in rows
    ]
