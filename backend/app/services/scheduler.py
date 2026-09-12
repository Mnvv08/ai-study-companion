"""
app/services/scheduler.py
─────────────────────────
Spaced-repetition scheduling, based on the SM-2 algorithm.

WHY THIS EXISTS
  The analytics layer can already tell a student which topics they get wrong.
  That answers "what am I bad at" but not "what should I open my laptop and
  study today" — and the second question is the one that actually changes
  behaviour.

  SM-2 answers it by spacing reviews according to how well a topic is known.
  Get a topic right repeatedly and the gap before the next review grows
  (1 day → 6 days → weeks). Get it wrong and the gap collapses back to a day.
  The effect is that study time concentrates on weak material automatically,
  instead of being spread evenly over things the student already knows.

WHY SM-2 AND NOT SOMETHING NEWER
  Newer schedulers (FSRS and friends) fit better but need a corpus of review
  history to train on. SM-2 needs three numbers per topic and no training
  data, which matches what this app actually has. It is also simple enough to
  test exhaustively, which matters more here than squeezing out the last few
  percent of scheduling accuracy.

GRADING
  Classic SM-2 expects a 0–5 self-reported grade. This app has something
  better: measured accuracy across the questions tagged with a topic in a
  quiz attempt. That fraction maps onto the 0–5 scale, so the grade reflects
  what the student actually did rather than how they felt about it.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

# Below this grade, SM-2 treats the review as a failure and restarts the topic.
PASSING_GRADE = 3

# Ease factor floor from the original algorithm. Without it, repeatedly failed
# topics drift toward a zero interval and get scheduled many times a day,
# which is punishing rather than useful.
MIN_EASE_FACTOR = 1.3

# Interval in days after the first and second successful reviews. These are
# fixed in SM-2; the ease factor only starts multiplying from the third.
FIRST_INTERVAL_DAYS = 1
SECOND_INTERVAL_DAYS = 6

# Cap so a well-known topic doesn't get scheduled beyond a realistic horizon.
# A student revising for a semester exam is not served by "see you in 2029".
MAX_INTERVAL_DAYS = 365


@dataclass(frozen=True)
class ScheduleState:
    """
    The three numbers SM-2 needs to schedule a topic, plus the resulting date.

    Frozen because scheduling is a pure calculation — `compute_next_review`
    takes a state and returns a new one rather than mutating in place, which
    keeps it trivial to test and impossible to half-update.
    """

    repetitions: int
    interval_days: int
    ease_factor: float
    due_at: datetime


def accuracy_to_grade(correct: int, total: int) -> int:
    """
    Convert measured accuracy on a topic into an SM-2 grade from 0 to 5.

    A topic with no questions in the attempt returns 0, but callers should
    skip such topics rather than record a failure for something untested.
    """
    if total <= 0:
        return 0

    # Truncate rather than round. Rounding puts the pass/fail boundary at
    # exactly half-correct, where Python's banker's rounding decides the tie
    # for us — 2 of 4 becomes grade 2, but 3 of 6 would also be 2.5 and the
    # behaviour starts to look arbitrary. Truncating states the rule plainly:
    # half-right is not knowing a topic, so it fails and comes back tomorrow.
    # The bias is toward more review, which is the right way to be wrong in
    # a study tool.
    return int((correct / total) * 5)


def compute_next_review(
    state: ScheduleState | None,
    grade: int,
    now: datetime | None = None,
) -> ScheduleState:
    """
    Apply one SM-2 step and return the updated schedule.

    Args:
        state: Current schedule for this topic, or None if never reviewed.
        grade: Performance on this review, 0 (total blank) to 5 (perfect).
        now:   Injectable clock. Tests pass a fixed datetime; production
               leaves it None and gets the real one.

    Returns:
        A new ScheduleState. The input is never modified.
    """
    now = now or datetime.now(timezone.utc)
    grade = max(0, min(5, grade))

    repetitions = state.repetitions if state else 0
    ease_factor = state.ease_factor if state else 2.5

    # Ease factor moves on every review, including failures. The curve is
    # from the original algorithm: grade 5 nudges it up slightly, grade 3
    # holds roughly steady, below that it drops off sharply.
    ease_factor += 0.1 - (5 - grade) * (0.08 + (5 - grade) * 0.02)
    ease_factor = max(MIN_EASE_FACTOR, ease_factor)

    if grade < PASSING_GRADE:
        # Failure restarts the ladder. The topic comes back tomorrow, but the
        # reduced ease factor persists, so it will climb more slowly than a
        # topic that has never been failed.
        repetitions = 0
        interval_days = FIRST_INTERVAL_DAYS
    else:
        repetitions += 1
        if repetitions == 1:
            interval_days = FIRST_INTERVAL_DAYS
        elif repetitions == 2:
            interval_days = SECOND_INTERVAL_DAYS
        else:
            previous = state.interval_days if state else SECOND_INTERVAL_DAYS
            interval_days = round(previous * ease_factor)

    interval_days = max(1, min(MAX_INTERVAL_DAYS, interval_days))

    return ScheduleState(
        repetitions=repetitions,
        interval_days=interval_days,
        ease_factor=round(ease_factor, 4),
        due_at=now + timedelta(days=interval_days),
    )
