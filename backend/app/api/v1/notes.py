"""
app/api/v1/notes.py
───────────────────
Endpoint for generating structured study notes from uploaded documents.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.file import UploadedFile
from app.schemas.rag import GenerateNotesRequest, GenerateNotesResponse
from app.services.llm_client import LLMClientService

router = APIRouter(prefix="/generate", tags=["AI Generation"])


@router.post("/notes", response_model=GenerateNotesResponse)
def generate_notes(
    request: GenerateNotesRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Generates structured, exam-ready study notes for an uploaded document.
    """
    db_file = (
        db.query(UploadedFile)
        .filter(UploadedFile.id == request.file_id, UploadedFile.user_id == current_user.id)
        .first()
    )
    if not db_file:
        raise HTTPException(status_code=404, detail="File not found")

    if not db_file.extracted_text:
        raise HTTPException(
            status_code=400, detail="File has no extracted text available."
        )

    llm_service = LLMClientService()
    try:
        notes_json = llm_service.generate_study_notes(db_file.extracted_text)
        return GenerateNotesResponse(
            file_id=db_file.id,
            title=notes_json.get("title", db_file.filename),
            sections=notes_json.get("sections", []),
            key_terms=notes_json.get("key_terms", []),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate study notes: {str(e)}",
        )
