"""
app/api/v1/documents.py
───────────────────────
Document management endpoints: upload, status tracking, retrieval, and deletion.

Key Design Decisions:
  1. Validation at the edge: Reject non-PDFs and oversized files BEFORE saving to disk.
  2. Atomic operations: Clean up orphan files if the DB transaction fails.
  3. Strict authorization: All endpoints require valid JWT and enforce ownership checks.
"""

import os
import re
import uuid
import logging
from typing import List
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from app.db.session import get_db
from app.core.config import settings
from app.core.security import get_current_user
from app.models.user import User
from app.models.file import Document
from app.schemas.file import (
    DocumentResponse,
    DocumentStatusResponse,
    DocumentDetailResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/documents", tags=["Documents"])


def sanitize_filename(filename: str) -> str:
    """Strip dangerous characters and paths from uploaded filenames."""
    base_name = os.path.basename(filename)
    # Allow alphanumeric, underscore, hyphen, and period
    clean_name = re.sub(r"[^\w\s\.-]", "", base_name).strip()
    return clean_name or "document.pdf"


@router.post(
    "/upload",
    response_model=DocumentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload a PDF study document",
)
async def upload_document(
    file: UploadFile = File(..., description="PDF study document file"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Upload and validate a PDF study document.

    Validations enforced:
      1. File type check: Must be '.pdf' extension (reject others with 400 Bad Request).
      2. File size check: Must not exceed MAX_UPLOAD_SIZE_MB (reject with 413 Payload Too Large).
      3. Non-empty check: File must contain data > 0 bytes.

    On success:
      - Saves file to local uploads directory with a collision-free UUID prefix.
      - Creates a row in PostgreSQL `documents` table with status='pending'.
      - If DB insertion fails, automatically removes the written file to avoid orphans.
    """
    raw_filename = file.filename or "document.pdf"
    clean_filename = sanitize_filename(raw_filename)
    
    # ── 1. Edge Validation: File Extension / Type ──────────────────
    if not clean_filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid file type '{clean_filename}'. Only PDF files are supported in Phase 1.",
        )

    # ── 2. Edge Validation: File Content & Size ────────────────────
    try:
        content = await file.read()
    except Exception as err:
        logger.error(f"Error reading uploaded stream: {err}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Could not read uploaded file content.",
        )

    file_size = len(content)

    if file_size == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The uploaded PDF file is empty.",
        )

    if file_size > settings.max_upload_size_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=(
                f"File size ({file_size / (1024 * 1024):.2f}MB) exceeds the maximum allowed "
                f"limit of {settings.MAX_UPLOAD_SIZE_MB}MB."
            ),
        )

    # ── 3. Save to Disk with Unique Prefix ──────────────────────────
    saved_file_path = None
    try:
        os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
        unique_filename = f"{uuid.uuid4()}_{clean_filename}"
        saved_file_path = os.path.join(settings.UPLOAD_DIR, unique_filename)

        with open(saved_file_path, "wb") as f:
            f.write(content)
    except OSError as io_err:
        logger.error(f"Disk write failure for file '{clean_filename}': {io_err}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save document to storage. Please try again.",
        )

    # ── 4. Save Record to Database (Atomic with Disk Cleanup) ───────
    try:
        db_document = Document(
            user_id=current_user.id,
            filename=clean_filename,
            file_path=saved_file_path,
            file_size_bytes=file_size,
            file_type="pdf",
            status="pending",
        )
        db.add(db_document)
        db.commit()
        db.refresh(db_document)
        return db_document
    except SQLAlchemyError as db_err:
        db.rollback()
        logger.error(f"Database insertion failure for document '{clean_filename}': {db_err}")
        # Clean up file on disk so we don't leave orphan files
        if saved_file_path and os.path.exists(saved_file_path):
            try:
                os.remove(saved_file_path)
            except OSError:
                pass
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to record document metadata in database.",
        )


@router.get(
    "/{document_id}/status",
    response_model=DocumentStatusResponse,
    summary="Get document processing status",
)
def get_document_status(
    document_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Check the current processing status of a document ('pending', 'processed', or 'failed').
    Enforces user ownership — returns 404 if the document does not exist or belongs to another user.
    """
    doc = (
        db.query(Document)
        .filter(Document.id == document_id, Document.user_id == current_user.id)
        .first()
    )
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found.",
        )

    return DocumentStatusResponse(
        id=doc.id,
        filename=doc.filename,
        status=doc.status,
        error_message=doc.error_message,
        created_at=doc.created_at,
    )


@router.get(
    "/",
    response_model=List[DocumentResponse],
    summary="List all uploaded documents for the current user",
)
def list_documents(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all documents owned by the authenticated student."""
    return (
        db.query(Document)
        .filter(Document.user_id == current_user.id)
        .order_by(Document.created_at.desc())
        .all()
    )


@router.get(
    "/{document_id}",
    response_model=DocumentDetailResponse,
    summary="Get document details by ID",
)
def get_document_detail(
    document_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get metadata and extracted text preview for a specific document."""
    doc = (
        db.query(Document)
        .filter(Document.id == document_id, Document.user_id == current_user.id)
        .first()
    )
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found.",
        )

    preview = (
        doc.extracted_text[:300] + "..."
        if doc.extracted_text and len(doc.extracted_text) > 300
        else doc.extracted_text
    )

    return DocumentDetailResponse(
        id=doc.id,
        filename=doc.filename,
        file_size_bytes=doc.file_size_bytes,
        file_type=doc.file_type,
        status=doc.status,
        created_at=doc.created_at,
        extracted_text_preview=preview,
    )


@router.delete(
    "/{document_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a document and its file on disk",
)
def delete_document(
    document_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a document record from PostgreSQL and remove its file from disk."""
    doc = (
        db.query(Document)
        .filter(Document.id == document_id, Document.user_id == current_user.id)
        .first()
    )
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found.",
        )

    # Clean up physical file
    if os.path.exists(doc.file_path):
        try:
            os.remove(doc.file_path)
        except OSError as err:
            logger.warning(f"Could not remove file on disk '{doc.file_path}': {err}")

    db.delete(doc)
    db.commit()
    return None
