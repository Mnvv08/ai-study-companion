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

import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.file import Document
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
def generate_flashcards(
    request: GenerateFlashcardsRequest,
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
        doc_id = request.target_document_id
    except ValueError as val_err:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(val_err))

    db_doc, content = _get_user_document_content(doc_id, current_user.id, db)
    llm_service = LLMClientService()

    try:
        cards = llm_service.generate_flashcards(text_content=content)
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
    "/mcqs/generate",
    response_model=GenerateMCQResponse,
    summary="Generate MCQs with 4 options and correct_index",
)
@router.post(
    "/mcq/generate",
    response_model=GenerateMCQResponse,
    include_in_schema=False,
)
@router.post(
    "/generate/mcq",
    response_model=GenerateMCQResponse,
    include_in_schema=False,
)
def generate_mcqs(
    request: GenerateMCQRequest,
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
        doc_id = request.target_document_id
    except ValueError as val_err:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(val_err))

    db_doc, content = _get_user_document_content(doc_id, current_user.id, db)
    llm_service = LLMClientService()

    try:
        mcqs = llm_service.generate_mcqs(text_content=content)
        return GenerateMCQResponse(document_id=db_doc.id, questions=mcqs)
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


@router.post(
    "/short-answer/generate",
    response_model=GenerateShortAnswerResponse,
    summary="Generate short-answer exam questions with model answers",
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
def generate_short_questions(
    request: GenerateShortAnswerRequest,
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
        doc_id = request.target_document_id
    except ValueError as val_err:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(val_err))

    db_doc, content = _get_user_document_content(doc_id, current_user.id, db)
    llm_service = LLMClientService()

    try:
        questions = llm_service.generate_short_questions(text_content=content)
        return GenerateShortAnswerResponse(document_id=db_doc.id, questions=questions)
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
