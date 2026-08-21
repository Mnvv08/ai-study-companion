"""
app/api/v1/files.py
───────────────────
File management endpoints: upload, list, get detail, delete.
"""

import os
import uuid
from typing import List
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.config import settings
from app.core.security import get_current_user
from app.models.user import User
from app.models.file import Document, UploadedFile
from app.schemas.file import FileResponse, FileDetailResponse
from app.services.extraction import extract_text_from_pdf

router = APIRouter(prefix="/files", tags=["Files"])


@router.post("/upload", response_model=FileResponse, status_code=status.HTTP_201_CREATED)
async def upload_file(
    file: UploadedFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Upload a study document (PDF only in Phase 1).

    Validations:
      1. File extension must be in ALLOWED_EXTENSIONS (pdf).
      2. File size must be under MAX_UPLOAD_SIZE_MB (20MB default).
      3. File must contain readable text.
    """
    filename = file.filename or "file.pdf"
    ext = filename.split(".")[-1].lower() if "." in filename else ""

    if ext not in settings.allowed_extensions_list:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file format '.{ext}'. Allowed formats: {settings.ALLOWED_EXTENSIONS}",
        )

    # Read content to check file size
    contents = await file.read()
    file_size = len(contents)

    if file_size > settings.max_upload_size_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File exceeds maximum allowed size of {settings.MAX_UPLOAD_SIZE_MB}MB",
        )

    # Ensure upload directory exists
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)

    # Save to disk with unique filename to prevent collisions
    unique_filename = f"{uuid.uuid4()}_{filename}"
    file_path = os.path.join(settings.UPLOAD_DIR, unique_filename)

    with open(file_path, "wb") as f:
        f.write(contents)

    # Extract text from saved file
    try:
        extracted_text = extract_text_from_pdf(file_path)
        status_flag = "processed"
    except ValueError as err:
        # File is corrupt or unscannable plain text
        os.remove(file_path)  # Cleanup disk
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Text extraction failed: {str(err)}",
        )

    # Save metadata in DB
    db_file = UploadedFile(
        user_id=current_user.id,
        filename=filename,
        file_path=file_path,
        file_size_bytes=file_size,
        file_type=ext,
        extracted_text=extracted_text,
        status=status_flag,
    )
    db.add(db_file)
    db.commit()
    db.refresh(db_file)

    return db_file


@router.get("/", response_model=List[FileResponse])
def list_files(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all files uploaded by the authenticated user."""
    return (
        db.query(UploadedFile)
        .filter(UploadedFile.user_id == current_user.id)
        .order_by(UploadedFile.created_at.desc())
        .all()
    )


@router.get("/{file_id}", response_model=FileDetailResponse)
def get_file(
    file_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get detailed information about a specific file including preview of extracted text."""
    db_file = (
        db.query(UploadedFile)
        .filter(UploadedFile.id == file_id, UploadedFile.user_id == current_user.id)
        .first()
    )
    if not db_file:
        raise HTTPException(status_code=404, detail="File not found")

    preview = (
        db_file.extracted_text[:300] + "..."
        if db_file.extracted_text and len(db_file.extracted_text) > 300
        else db_file.extracted_text
    )

    return FileDetailResponse(
        id=db_file.id,
        filename=db_file.filename,
        file_size_bytes=db_file.file_size_bytes,
        file_type=db_file.file_type,
        status=db_file.status,
        created_at=db_file.created_at,
        extracted_text_preview=preview,
    )


@router.delete("/{file_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_file(
    file_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a file from database and disk."""
    db_file = (
        db.query(UploadedFile)
        .filter(UploadedFile.id == file_id, UploadedFile.user_id == current_user.id)
        .first()
    )
    if not db_file:
        raise HTTPException(status_code=404, detail="File not found")

    if os.path.exists(db_file.file_path):
        try:
            os.remove(db_file.file_path)
        except OSError:
            pass

    db.delete(db_file)
    db.commit()
    return None
