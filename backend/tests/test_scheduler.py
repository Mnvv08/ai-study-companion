"""
tests/test_scheduler.py
───────────────────────
Unit tests for the SM-2 scheduling arithmetic.

No database and no HTTP here — `compute_next_review` is a pure function, so
these tests pin the algorithm's behaviour directly. The clock is injected so
assertions about due dates are exact rather than approximate.
"""

from datetime import datetime, timedelta, timezone

import pytest

from app.services.scheduler import (
    FIRST_INTERVAL_DAYS,
    MAX_INTERVAL_DAYS,
    MIN_EASE_FACTOR,
    SECOND_INTERVAL_DAYS,
    ScheduleState,
    accuracy_to_grade,
    compute_next_review,
)

NOW = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)


# ── accuracy_to_grade ────────────────────────────────────────────────

@pytest.mark.parametrize(
    "correct,total,expected",
    [
        (0, 4, 0),   # nothing right
        (2, 4, 2),   # half right → fails; half-knowing is not knowing
        (3, 4, 3),   # three quarters → passes, just
        (4, 4, 5),   # perfect
        (1, 3, 1),   # a third → failing
        (5, 6, 4),   # strong but imperfect
    ],
)
def test_accuracy_maps_to_grade(correct, total, expected):
    assert accuracy_to_grade(correct, total) == expected


def test_accuracy_with_no_questions_is_zero():
    """Guard against divide-by-zero; callers skip topics with no questions."""
    assert accuracy_to_grade(0, 0) == 0


# ── first review ─────────────────────────────────────────────────────

def test_first_successful_review_schedules_one_day_out():
    state = compute_next_review(None, grade=5, now=NOW)
    assert state.repetitions == 1
    assert state.interval_days == FIRST_INTERVAL_DAYS
    assert state.due_at == NOW + timedelta(days=1)


def test_first_failed_review_still_comes_back_tomorrow():
    state = compute_next_review(None, grade=1, now=NOW)
    assert state.repetitions == 0
    assert state.interval_days == FIRST_INTERVAL_DAYS


# ── the interval ladder ──────────────────────────────────────────────

def test_second_success_jumps_to_six_days():
    first = compute_next_review(None, grade=5, now=NOW)
    second = compute_next_review(first, grade=5, now=NOW)
    assert second.repetitions == 2
    assert second.interval_days == SECOND_INTERVAL_DAYS


def test_third_success_multiplies_by_ease_factor():
    """From the third review on, the interval grows geometrically."""
    s = compute_next_review(None, grade=5, now=NOW)
    s = compute_next_review(s, grade=5, now=NOW)
    third = compute_next_review(s, grade=5, now=NOW)

    assert third.repetitions == 3
    assert third.interval_days == round(SECOND_INTERVAL_DAYS * third.ease_factor)
    assert third.interval_days > SECOND_INTERVAL_DAYS


def test_intervals_grow_monotonically_under_repeated_success():
    state = None
    intervals = []
    for _ in range(6):
        state = compute_next_review(state, grade=5, now=NOW)
        intervals.append(state.interval_days)
    assert intervals == sorted(intervals)
    assert intervals[-1] > intervals[0]


# ── failure behaviour ────────────────────────────────────────────────

def test_failure_collapses_a_long_interval_back_to_one_day():
    """
    The core promise of spaced repetition: forgetting something brings it
    straight back, however well-known it previously was.
    """
    state = None
    for _ in range(4):
        state = compute_next_review(state, grade=5, now=NOW)
    assert state.interval_days > 10

    failed = compute_next_review(state, grade=1, now=NOW)
    assert failed.repetitions == 0
    assert failed.interval_days == FIRST_INTERVAL_DAYS


def test_failure_lowers_ease_so_relearning_is_slower():
    strong = compute_next_review(None, grade=5, now=NOW)
    failed = compute_next_review(strong, grade=0, now=NOW)
    assert failed.ease_factor < strong.ease_factor


def test_ease_factor_never_drops_below_the_floor():
    """Without the floor, repeated failure drives intervals toward zero."""
    state = None
    for _ in range(20):
        state = compute_next_review(state, grade=0, now=NOW)
    assert state.ease_factor == pytest.approx(MIN_EASE_FACTOR)
    assert state.interval_days >= 1


# ── boundaries ───────────────────────────────────────────────────────

def test_half_correct_fails_and_three_quarters_passes():
    """The pass boundary sits between 50% and 75% accuracy on a topic."""
    assert accuracy_to_grade(2, 4) < 3
    assert accuracy_to_grade(3, 4) >= 3


def test_grade_three_passes_and_grade_two_fails():
    """Grade 3 is the pass mark in SM-2. Check both sides of the line."""
    passed = compute_next_review(None, grade=3, now=NOW)
    failed = compute_next_review(None, grade=2, now=NOW)
    assert passed.repetitions == 1
    assert failed.repetitions == 0


def test_interval_is_capped():
    state = None
    for _ in range(40):
        state = compute_next_review(state, grade=5, now=NOW)
    assert state.interval_days <= MAX_INTERVAL_DAYS


def test_out_of_range_grades_are_clamped_not_rejected():
    assert compute_next_review(None, grade=99, now=NOW).repetitions == 1
    assert compute_next_review(None, grade=-5, now=NOW).repetitions == 0


def test_input_state_is_never_mutated():
    """ScheduleState is frozen; this pins the no-side-effects contract."""
    original = ScheduleState(
        repetitions=3, interval_days=15, ease_factor=2.5, due_at=NOW
    )
    compute_next_review(original, grade=0, now=NOW)
    assert original.repetitions == 3
    assert original.interval_days == 15
