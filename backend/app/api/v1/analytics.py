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
from app.models.file import Document
from app.models.quiz import QuizAttempt, AttemptAnswer, Question, Quiz
from app.schemas.analytics import WeakTopicsResponse, RecommendationsResponse

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


@router.get("/recommendations", response_model=RecommendationsResponse)
def get_recommendations(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Retrieve revision recommendations based on the top 3 weakest topics.
    Excludes topics with fewer than 3 attempted questions.
    """
    # 1. Fetch weak topics using the same logic as weak-topics
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

    # Take top 3 weakest
    top_3_weakest = weak_topics[:3]

    recommendations = []
    for wt in top_3_weakest:
        topic_name = wt["topic"]

        # Fetch associated document info for this topic and current user
        doc_info = (
            db.query(Document.id, Document.filename)
            .join(Quiz, Quiz.document_id == Document.id)
            .join(Question, Question.quiz_id == Quiz.id)
            .filter(Document.user_id == current_user.id)
            .filter(Question.topic_tag == topic_name)
            .first()
        )

        doc_id = doc_info[0] if doc_info else "unknown"
        doc_filename = doc_info[1] if doc_info else "unknown_document"

        if current_user.persona_mode:
            reason = f"Thoda aur focus chahiye, senior says: sirf {wt['accuracy_percentage']}% accuracy across {wt['total_attempted']} questions."
        else:
            reason = f"Only {wt['accuracy_percentage']}% accuracy across {wt['total_attempted']} questions"

        recommendations.append({
            "topic": topic_name,
            "reason": reason,
            "document_id": doc_id,
            "document_filename": doc_filename
        })

    return {
        "recommendations": recommendations
    }

