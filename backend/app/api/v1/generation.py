"""
app/api/v1/generation.py
────────────────────────
API router for AI generation features: Flashcards, MCQs, and Short-Answer Questions.

Workflow for Flashcards:
  1. Authenticate user and verify document ownership (404 on mismatch).
  2. Retrieve all document chunks from ChromaDB (or fallback to extracted text).
  3. Call LLM with exact system prompt to extract natural, testable active-recall cards with topic tags.
  4. Defensively parse and return JSON without persisting to DB yet.
"""

import uuid
import logging
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session
from app.core.rate_limiter import limiter

from app.db.session import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.file import Document
from app.models.quiz import Quiz, Question
from app.schemas.generation import (
    GenerateFlashcardsRequest,
    GenerateFlashcardsResponse,
    GenerateMCQRequest,
    GenerateMCQResponse,
    GenerateShortAnswerRequest,
    GenerateShortAnswerResponse,
    GenerateShortQRequest,
    GenerateShortQResponse,
)
from app.services.vector_store import VectorStoreService
from app.services.llm_client import LLMClientService
from app.core.cache import study_cache

logger = logging.getLogger(__name__)

router = APIRouter(tags=["AI Generation"])


def _get_user_document_content(doc_id: str, user_id: str, db: Session) -> "tuple[Document, str]":
    """Helper to verify document ownership and pull content from ChromaDB or text storage."""
    db_doc = (
        db.query(Document)
        .filter(Document.id == doc_id, Document.user_id == user_id)
        .first()
    )
    if not db_doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found.",
        )

    # Pull chunks from ChromaDB
    vector_service = VectorStoreService()
    chunks = vector_service.get_document_chunks(user_id=user_id, document_id=db_doc.id)

    if chunks:
        content = "\n\n".join(chunks)
    elif db_doc.extracted_text:
        content = db_doc.extracted_text
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Document contains no readable text for content generation.",
        )

    return db_doc, content


@router.post(
    "/flashcards/generate",
    response_model=GenerateFlashcardsResponse,
    summary="Generate active-recall flashcards from an uploaded document",
)
@router.post(
    "/generate/flashcards",
    response_model=GenerateFlashcardsResponse,
    include_in_schema=False,
)
@limiter.limit("20/minute")
def generate_flashcards(
    request: Request,
    payload: GenerateFlashcardsRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Generate concept-based active-recall flashcards from a study document.

    Rules:
      - Strictly grounded in document material.
      - Returns { front, back, topic } items.
      - Automatically decides card quantity based on content density.
    """
    try:
        doc_id = payload.target_document_id
    except ValueError as val_err:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(val_err))

    db_doc, content = _get_user_document_content(doc_id, current_user.id, db)
    llm_service = LLMClientService()

    # ── Cache Lookup & Eviction ────────────────────────────────────
    endpoint_key = "flashcards"
    if payload.force_regenerate:
        study_cache.invalidate(db_doc.id, endpoint_key)

    cached_cards = study_cache.get(db_doc.id, endpoint_key)
    if cached_cards is not None:
        return GenerateFlashcardsResponse(document_id=db_doc.id, flashcards=cached_cards)

    # ── Call LLM ───────────────────────────────────────────────────
    try:
        cards = llm_service.generate_flashcards(text_content=content, persona_mode=current_user.persona_mode)
        study_cache.set(db_doc.id, endpoint_key, cards)
        return GenerateFlashcardsResponse(document_id=db_doc.id, flashcards=cards)
    except RuntimeError as llm_err:
        logger.error(f"LLM flashcard error for document {db_doc.id}: {llm_err}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"AI service error during flashcard generation: {str(llm_err)}",
        )
    except Exception as e:
        logger.error(f"Unexpected flashcard generation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate flashcards.",
        )


@router.post(
    "/mcq/generate",
    response_model=GenerateMCQResponse,
    include_in_schema=False,
)
@router.post(
    "/mcqs/generate",
    response_model=GenerateMCQResponse,
    summary="Generate Multiple Choice Questions (MCQs) from a document",
)
@router.post(
    "/generate/mcq",
    response_model=GenerateMCQResponse,
    include_in_schema=False,
)
@limiter.limit("20/minute")
def generate_mcqs(
    request: Request,
    payload: GenerateMCQRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Generate Multiple Choice Questions (MCQs).

    Rules:
      - Strictly grounded in document material.
      - Exactly 4 options per question with 1 correct answer (correct_index 0-3).
      - Tagged with topic for weak-area tracking.
      - Malformed questions with != 4 options or out-of-range correct_index are dropped.
    """
    try:
        doc_id = payload.target_document_id
    except ValueError as val_err:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(val_err))

    db_doc, content = _get_user_document_content(doc_id, current_user.id, db)
    llm_service = LLMClientService()

    # ── Cache Lookup & Eviction ────────────────────────────────────
    endpoint_key = "mcqs"
    if payload.force_regenerate:
        study_cache.invalidate(db_doc.id, endpoint_key)

    mcqs = study_cache.get(db_doc.id, endpoint_key)

    if mcqs is None:
        try:
            mcqs = llm_service.generate_mcqs(text_content=content, persona_mode=current_user.persona_mode)
            study_cache.set(db_doc.id, endpoint_key, mcqs)
        except RuntimeError as llm_err:
            logger.error(f"LLM MCQ generation error for document {db_doc.id}: {llm_err}")
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"AI service error during MCQ generation: {str(llm_err)}",
            )
        except Exception as e:
            logger.error(f"Unexpected MCQ generation error: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to generate MCQs.",
            )

    # Persist the generated MCQs to the database inside a single transaction
    quiz_id = str(uuid.uuid4())
    try:
        new_quiz = Quiz(
            id=quiz_id,
            document_id=db_doc.id,
            quiz_type="mcq"
        )
        db.add(new_quiz)

        questions_list = []
        for item in mcqs:
            q_id = str(uuid.uuid4())
            db_q = Question(
                id=q_id,
                quiz_id=quiz_id,
                question_text=item["question"],
                options=item["options"],
                correct_answer=str(item["correct_index"]),
                topic_tag=item["topic"]
            )
            db.add(db_q)

            questions_list.append({
                "id": q_id,
                "quiz_id": quiz_id,
                "question": item["question"],
                "options": item["options"],
                "correct_index": item["correct_index"],
                "topic": item["topic"]
            })

        db.commit()
        return GenerateMCQResponse(
            document_id=db_doc.id,
            quiz_id=quiz_id,
            questions=questions_list
        )
    except Exception as db_err:
        db.rollback()
        logger.error(f"Database error persisting MCQ quiz for document {db_doc.id}: {db_err}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save generated MCQs to the database.",
        )


@router.post(
    "/short-answer/generate",
    response_model=GenerateShortAnswerResponse,
    summary="Generate short-answer conceptual exam questions from a document",
)
@router.post(
    "/shortq/generate",
    response_model=GenerateShortAnswerResponse,
    include_in_schema=False,
)
@router.post(
    "/generate/short-answer",
    response_model=GenerateShortAnswerResponse,
    include_in_schema=False,
)
@router.post(
    "/generate/shortq",
    response_model=GenerateShortAnswerResponse,
    include_in_schema=False,
)
@limiter.limit("20/minute")
def generate_short_questions(
    request: Request,
    payload: GenerateShortAnswerRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Generate short-answer conceptual exam questions.

    Rules:
      - Strictly grounded in document material.
      - Requires 1-3 sentence answers with a concise model answer.
      - Tagged with topic for weak-area tracking.
    """
    try:
        doc_id = payload.target_document_id
    except ValueError as val_err:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(val_err))

    db_doc, content = _get_user_document_content(doc_id, current_user.id, db)
    llm_service = LLMClientService()

    # ── Cache Lookup & Eviction ────────────────────────────────────
    endpoint_key = "short_answer"
    if payload.force_regenerate:
        study_cache.invalidate(db_doc.id, endpoint_key)

    questions = study_cache.get(db_doc.id, endpoint_key)

    if questions is None:
        try:
            questions = llm_service.generate_short_questions(text_content=content, persona_mode=current_user.persona_mode)
            study_cache.set(db_doc.id, endpoint_key, questions)
        except RuntimeError as llm_err:
            logger.error(f"LLM short-answer generation error for document {db_doc.id}: {llm_err}")
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"AI service error during short-answer generation: {str(llm_err)}",
            )
        except Exception as e:
            logger.error(f"Unexpected short-answer generation error: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to generate short-answer questions.",
            )

    # Persist the generated short-answer questions to the database inside a single transaction
    quiz_id = str(uuid.uuid4())
    try:
        new_quiz = Quiz(
            id=quiz_id,
            document_id=db_doc.id,
            quiz_type="short_answer"
        )
        db.add(new_quiz)

        questions_list = []
        for item in questions:
            q_id = str(uuid.uuid4())
            db_q = Question(
                id=q_id,
                quiz_id=quiz_id,
                question_text=item["question"],
                options=None,
                correct_answer=item["model_answer"],
                topic_tag=item["topic"]
            )
            db.add(db_q)

            questions_list.append({
                "id": q_id,
                "quiz_id": quiz_id,
                "question": item["question"],
                "model_answer": item["model_answer"],
                "topic": item["topic"]
            })

        db.commit()
        return GenerateShortAnswerResponse(
            document_id=db_doc.id,
            quiz_id=quiz_id,
            questions=questions_list
        )
    except Exception as db_err:
        db.rollback()
        logger.error(f"Database error persisting short-answer quiz for document {db_doc.id}: {db_err}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save generated short-answer questions to the database.",
        )
