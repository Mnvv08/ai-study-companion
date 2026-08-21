"""
app/api/v1/analytics.py
───────────────────────
API router for student analytics: weak topic detection.
"""

import logging
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from sqlalchemy import func, case

from app.db.session import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.quiz import QuizAttempt, AttemptAnswer, Question
from app.schemas.analytics import WeakTopicsResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/analytics", tags=["Analytics"])


@router.get("/weak-topics", response_model=WeakTopicsResponse)
def get_weak_topics(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Retrieve the current user's weak topics based on quiz history.
    Excludes topics with fewer than 3 attempted questions to prevent statistical noise.
    """
    # Join: QuizAttempt -> AttemptAnswer -> Question
    # Group by topic tag and calculate total and correct attempts
    results = (
        db.query(
            Question.topic_tag.label("topic"),
            func.count(AttemptAnswer.id).label("total_attempted"),
            func.sum(case((AttemptAnswer.is_correct == True, 1), else_=0)).label("correct_count"),
        )
        .join(AttemptAnswer, AttemptAnswer.question_id == Question.id)
        .join(QuizAttempt, QuizAttempt.id == AttemptAnswer.attempt_id)
        .filter(QuizAttempt.user_id == current_user.id)
        .group_by(Question.topic_tag)
        .having(func.count(AttemptAnswer.id) >= 3)
        .all()
    )

    weak_topics = []
    for r in results:
        total = int(r.total_attempted)
        correct = int(r.correct_count or 0)
        accuracy = (correct / total) * 100.0 if total > 0 else 0.0

        weak_topics.append({
            "topic": r.topic,
            "total_attempted": total,
            "correct_count": correct,
            "accuracy_percentage": round(accuracy, 2)
        })

    # Sort from weakest (lowest accuracy) to strongest (highest accuracy)
    weak_topics.sort(key=lambda x: (x["accuracy_percentage"], x["total_attempted"]))

    return {
        "weak_topics": weak_topics
    }
