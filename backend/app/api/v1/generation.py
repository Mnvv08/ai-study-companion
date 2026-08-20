"""
app/api/v1/generation.py
────────────────────────
API router for AI generation features: Flashcards, MCQs, and Short-Answer Questions.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.file import UploadedFile
from app.schemas.generation import (
    GenerateFlashcardsRequest,
    GenerateFlashcardsResponse,
    GenerateMCQRequest,
    GenerateMCQResponse,
    GenerateShortQRequest,
    GenerateShortQResponse,
)
from app.services.llm_client import LLMClientService

router = APIRouter(prefix="/generate", tags=["AI Generation"])


def _get_user_file_or_404(file_id: str, user_id: str, db: Session) -> UploadedFile:
    """Helper to verify file existence and user ownership."""
    db_file = (
        db.query(UploadedFile)
        .filter(UploadedFile.id == file_id, UploadedFile.user_id == user_id)
        .first()
    )
    if not db_file:
        raise HTTPException(status_code=404, detail="File not found")
    if not db_file.extracted_text:
        raise HTTPException(status_code=400, detail="File has no extracted text available")
    return db_file


@router.post("/flashcards", response_model=GenerateFlashcardsResponse)
def generate_flashcards(
    request: GenerateFlashcardsRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Generate active-recall flashcards from an uploaded document."""
    db_file = _get_user_file_or_404(request.file_id, current_user.id, db)
    llm_service = LLMClientService()

    try:
        cards = llm_service.generate_flashcards(
            text_content=db_file.extracted_text, count=request.count
        )
        return GenerateFlashcardsResponse(file_id=db_file.id, flashcards=cards)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate flashcards: {str(e)}",
        )


@router.post("/mcq", response_model=GenerateMCQResponse)
def generate_mcqs(
    request: GenerateMCQRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Generate Multiple Choice Questions (MCQs) with options and explanations."""
    db_file = _get_user_file_or_404(request.file_id, current_user.id, db)
    llm_service = LLMClientService()

    try:
        mcqs = llm_service.generate_mcqs(
            text_content=db_file.extracted_text, count=request.count
        )
        return GenerateMCQResponse(file_id=db_file.id, mcqs=mcqs)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate MCQs: {str(e)}",
        )


@router.post("/shortq", response_model=GenerateShortQResponse)
def generate_short_questions(
    request: GenerateShortQRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Generate short-answer conceptual exam questions with model answers and evaluation points."""
    db_file = _get_user_file_or_404(request.file_id, current_user.id, db)
    llm_service = LLMClientService()

    try:
        questions = llm_service.generate_short_questions(
            text_content=db_file.extracted_text, count=request.count
        )
        return GenerateShortQResponse(file_id=db_file.id, questions=questions)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate short questions: {str(e)}",
        )
