"""
app/schemas/file.py
───────────────────
Pydantic schemas for document upload, processing status, and document details.
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict


class DocumentResponse(BaseModel):
    id: str
    filename: str
    file_size_bytes: int
    file_type: str
    status: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DocumentStatusResponse(BaseModel):
    id: str
    filename: str
    status: str
    error_message: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DocumentDetailResponse(DocumentResponse):
    extracted_text_preview: Optional[str] = None


# Backwards compatibility aliases
FileResponse = DocumentResponse
FileDetailResponse = DocumentDetailResponse
