"""
app/models/review.py
────────────────────
Per-user, per-topic spaced-repetition state.

One row per (user, topic) pair. The row is the student's relationship with
that topic over time: how many times in a row they've passed it, how far
apart the reviews have grown, and when it next comes due.

Note the deliberate absence of a document foreign key. A topic like
"transaction isolation" may appear across several uploaded documents, and the
student either knows it or doesn't — scheduling it separately per document
would fragment the history and schedule the same material three times.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class TopicReview(Base):
    __tablename__ = "topic_reviews"

    # A user cannot have two schedules for the same topic. Enforced in the
    # database rather than only in application code, because a double-submit
    # racing itself would otherwise create a duplicate and silently split the
    # topic's history in two.
    __table_args__ = (
        UniqueConstraint("user_id", "topic", name="uq_topic_reviews_user_topic"),
    )

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Matches Question.topic_tag, which is String(100).
    topic: Mapped[str] = mapped_column(String(100), nullable=False, index=True)

    # ── SM-2 state ────────────────────────────────────────────────────
    # Consecutive successful reviews. Resets to 0 on any failure.
    repetitions: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # Current gap between reviews, in days.
    interval_days: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    # How quickly the interval grows. Starts at 2.5, floors at 1.3.
    ease_factor: Mapped[float] = mapped_column(Float, nullable=False, default=2.5)

    # ── History ───────────────────────────────────────────────────────
    due_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    last_reviewed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    total_reviews: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # Times this topic has been failed after previously being passed. Kept
    # separate from repetitions (which resets) so a topic that is repeatedly
    # relearned and forgotten stays visible as a problem area.
    lapses: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    user: Mapped["User"] = relationship("User")
