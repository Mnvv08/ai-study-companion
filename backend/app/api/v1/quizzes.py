"""
app/api/v1/quizzes.py
─────────────────────
API router for Quizzes: retrieval for attempts and submissions.
"""

import uuid
import logging
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.quiz import Quiz, QuizAttempt, AttemptAnswer
from app.models.file import Document
from app.schemas.quiz import QuizAttemptResponse, QuizSubmitRequest, QuizSubmitResponse, QuizHistoryItem

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/quizzes", tags=["Quizzes"])


@router.get("/history", response_model=List[QuizHistoryItem])
def get_quiz_history(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Retrieve the current user's past quiz attempts.
    """
    attempts = (
        db.query(QuizAttempt)
        .join(Quiz, QuizAttempt.quiz_id == Quiz.id)
        .join(Document, Quiz.document_id == Document.id)
        .filter(QuizAttempt.user_id == current_user.id)
        .order_by(QuizAttempt.attempted_at.desc())
        .all()
    )

    results = []
    for attempt in attempts:
        results.append(QuizHistoryItem(
            quiz_id=attempt.quiz_id,
            document_id=attempt.quiz.document_id,
            document_filename=attempt.quiz.document.filename,
            quiz_type=attempt.quiz.quiz_type,
            score=attempt.score,
            attempted_at=attempt.attempted_at,
        ))

    return results


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


@router.post("/{quiz_id}/submit", response_model=QuizSubmitResponse)
def submit_quiz(
    quiz_id: str,
    payload: QuizSubmitRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Submit answers for a quiz attempt, grade them, and persist the results.
    """
    # Fetch quiz
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

    # Create lookup map of question_id -> Question
    question_map = {q.id: q for q in quiz.questions}

    # Verify that all submitted question_ids actually belong to this quiz
    for ans in payload.answers:
        if ans.question_id not in question_map:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Question ID {ans.question_id} does not belong to this quiz.",
            )

    # Map question_id to student_answer
    submission_map = {ans.question_id: ans.student_answer for ans in payload.answers}

    correct_count = 0
    feedback_items = []
    answers_to_create = []

    attempt_id = str(uuid.uuid4())

    for question in quiz.questions:
        has_submitted = question.id in submission_map
        student_ans = submission_map[question.id].strip() if has_submitted else ""
        correct_ans = question.correct_answer.strip()

        is_correct = False
        if has_submitted:
            if quiz.quiz_type == "mcq":
                # MCQ: exact index match (case-insensitive comparison as index string)
                is_correct = (student_ans.lower() == correct_ans.lower())
            else:
                # Short Answer: simple case-insensitive substring/keyword match
                is_correct = (student_ans.lower() in correct_ans.lower() or correct_ans.lower() in student_ans.lower())

        if is_correct:
            correct_count += 1

        feedback_items.append({
            "question_id": question.id,
            "question_text": question.question_text,
            "student_answer": student_ans,
            "correct_answer": correct_ans,
            "is_correct": is_correct,
        })

        answers_to_create.append(AttemptAnswer(
            id=str(uuid.uuid4()),
            attempt_id=attempt_id,
            question_id=question.id,
            student_answer=student_ans,
            is_correct=is_correct,
        ))

    total_questions = len(quiz.questions)
    score = (correct_count / total_questions) if total_questions > 0 else 0.0

    # Wrap writes in a transaction
    try:
        attempt = QuizAttempt(
            id=attempt_id,
            user_id=current_user.id,
            quiz_id=quiz.id,
            score=score,
        )
        db.add(attempt)
        for ans_db in answers_to_create:
            db.add(ans_db)
        db.commit()
    except Exception as db_err:
        db.rollback()
        logger.error(f"Failed to persist quiz attempt {attempt_id}: {db_err}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to record quiz submission to the database.",
        )

    return {
        "attempt_id": attempt_id,
        "quiz_id": quiz_id,
        "score": score,
        "questions_count": total_questions,
        "correct_count": correct_count,
        "feedback": feedback_items,
    }
