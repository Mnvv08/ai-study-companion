"""
app/api/v1/notes.py
───────────────────
Structured study notes generation endpoints.

Workflow:
  1. Authenticate user and verify document ownership (404 on mismatch).
  2. Retrieve all document chunks from ChromaDB (sorted chronologically) or fallback to extracted text.
  3. Call LLM with exact structured notes prompt.
  4. Defensively parse and return JSON to the frontend.
"""

import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.file import Document
from app.schemas.rag import GenerateNotesRequest, GenerateNotesResponse
from app.services.vector_store import VectorStoreService
from app.services.llm_client import LLMClientService

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Study Notes"])


@router.post(
    "/notes/generate",
    response_model=GenerateNotesResponse,
    summary="Generate structured, exam-ready study notes from a document",
)
@router.post(
    "/generate/notes",
    response_model=GenerateNotesResponse,
    include_in_schema=False,
)
def generate_notes(
    request: GenerateNotesRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Generates structured study notes from an uploaded course document.

    Steps:
      1. Verifies document ownership (returns 404 if document is not found or not owned).
      2. Retrieves document text chunks from vector store / storage.
      3. Passes text to LLM to produce structured sections, bullet points, and key definitions.
      4. Validates JSON defensively before returning.
    """
    try:
        doc_id = request.target_document_id
    except ValueError as val_err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(val_err),
        )

    # Verify ownership
    db_doc = (
        db.query(Document)
        .filter(Document.id == doc_id, Document.user_id == current_user.id)
        .first()
    )
    if not db_doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found.",
        )

    # ── Retrieve Document Chunks ──────────────────────────────────
    vector_service = VectorStoreService()
    chunks = vector_service.get_document_chunks(
        user_id=current_user.id,
        document_id=db_doc.id,
    )

    if chunks:
        # Reconstruct document content from ordered vector chunks
        study_content = "\n\n".join(chunks)
    elif db_doc.extracted_text:
        study_content = db_doc.extracted_text
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Document contains no readable text for note generation.",
        )

    # ── Call LLM for Structured Notes ─────────────────────────────
    llm_service = LLMClientService()
    try:
        notes_data = llm_service.generate_study_notes(study_content)
        return GenerateNotesResponse(
            document_id=db_doc.id,
            title=notes_data.get("title", db_doc.filename),
            sections=notes_data.get("sections", []),
            key_terms=notes_data.get("key_terms", []),
        )
    except RuntimeError as llm_err:
        logger.error(f"LLM notes generation failure for doc {db_doc.id}: {llm_err}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"AI service error during note generation: {str(llm_err)}",
        )
    except Exception as err:
        logger.error(f"Unexpected error in generate_notes endpoint: {err}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while generating study notes.",
        )
