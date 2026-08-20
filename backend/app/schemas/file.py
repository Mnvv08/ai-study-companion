"""
app/schemas/file.py
───────────────────
Pydantic schemas for file upload and file information responses.
"""

from pydantic import BaseModel
from datetime import datetime


class FileResponse(BaseModel):
    id: str
    filename: str
    file_size_bytes: int
    file_type: str
    status: str
    created_at: datetime

    class Config:
        from_attributes = True


class FileDetailResponse(FileResponse):
    extracted_text_preview: str | None = None
