"""
app/api/v1/quizzes.py
─────────────────────
API router for Quizzes: retrieval for attempts.
"""

import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.quiz import Quiz
from app.schemas.quiz import QuizAttemptResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/quizzes", tags=["Quizzes"])


@router.get("/{quiz_id}", response_model=QuizAttemptResponse)
def get_quiz(
    quiz_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Retrieve a quiz by its ID for a student attempt.
    Hides correct answers to ensure exam integrity.
    """
    quiz = db.query(Quiz).filter(Quiz.id == quiz_id).first()
    if not quiz:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Quiz not found.",
        )

    # Check ownership via linked document
    if quiz.document.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Quiz not found.",
        )

    # Prepare questions matching QuestionAttemptResponse schema
    questions_attempt = []
    for q in quiz.questions:
        questions_attempt.append({
            "id": q.id,
            "quiz_id": q.quiz_id,
            "question_text": q.question_text,
            "options": q.options,
            "topic_tag": q.topic_tag,
        })

    return {
        "id": quiz.id,
        "document_id": quiz.document_id,
        "quiz_type": quiz.quiz_type,
        "created_at": quiz.created_at,
        "questions": questions_attempt,
    }
