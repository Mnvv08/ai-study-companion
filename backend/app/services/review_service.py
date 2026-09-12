"""
app/services/review_service.py
──────────────────────────────
Turns a graded quiz attempt into spaced-repetition schedule updates.

The split is deliberate: `scheduler.py` holds the SM-2 arithmetic and touches
no database, while this module owns the database work and calls into it. That
way the algorithm can be tested exhaustively with plain values, and this layer
only has to be tested for "did it write the right rows".
"""

from __future__ import annotations

import logging
from collections import defaultdict
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.review import TopicReview
from app.services.scheduler import (
    PASSING_GRADE,
    ScheduleState,
    accuracy_to_grade,
    compute_next_review,
)

logger = logging.getLogger(__name__)


def record_attempt_reviews(
    db: Session,
    user_id: str,
    graded_answers: list[tuple[str, bool]],
    now: datetime | None = None,
) -> dict[str, int]:
    """
    Update each topic's schedule from one quiz attempt.

    Args:
        db:             Active session. This function adds to it but does NOT
                        commit — the caller owns the transaction so schedule
                        updates land atomically with the attempt itself.
        user_id:        Who sat the quiz.
        graded_answers: (topic_tag, is_correct) for every answered question.
        now:            Injectable clock for tests.

    Returns:
        topic -> grade awarded, useful for logging and for the API response.
    """
    now = now or datetime.now(timezone.utc)

    # Grade per topic, not per question. Two questions on the same topic in
    # one quiz are one piece of evidence about that topic, so they produce a
    # single scheduling decision rather than two competing ones.
    tally: dict[str, list[int]] = defaultdict(list)
    for topic, is_correct in graded_answers:
        tally[topic].append(1 if is_correct else 0)

    if not tally:
        return {}

    topics = list(tally.keys())
    existing = {
        row.topic: row
        for row in db.query(TopicReview)
        .filter(TopicReview.user_id == user_id, TopicReview.topic.in_(topics))
        .all()
    }

    grades: dict[str, int] = {}

    for topic, results in tally.items():
        grade = accuracy_to_grade(sum(results), len(results))
        grades[topic] = grade

        row = existing.get(topic)
        previous_state = (
            ScheduleState(
                repetitions=row.repetitions,
                interval_days=row.interval_days,
                ease_factor=row.ease_factor,
                due_at=row.due_at,
            )
            if row
            else None
        )

        next_state = compute_next_review(previous_state, grade, now=now)

        if row is None:
            db.add(
                TopicReview(
                    user_id=user_id,
                    topic=topic,
                    repetitions=next_state.repetitions,
                    interval_days=next_state.interval_days,
                    ease_factor=next_state.ease_factor,
                    due_at=next_state.due_at,
                    last_reviewed_at=now,
                    total_reviews=1,
                    lapses=0,
                )
            )
        else:
            # A lapse is failing something you had previously got right.
            # Failing a topic you never passed is just not having learned it
            # yet, which is a different thing and shouldn't inflate the count.
            if grade < PASSING_GRADE and row.repetitions > 0:
                row.lapses += 1

            row.repetitions = next_state.repetitions
            row.interval_days = next_state.interval_days
            row.ease_factor = next_state.ease_factor
            row.due_at = next_state.due_at
            row.last_reviewed_at = now
            row.total_reviews += 1

    logger.info("Updated %d topic schedules for user %s", len(grades), user_id)
    return grades
