"""
app/schemas/generation.py
──────────────────────────
Pydantic schemas for Flashcards, MCQs, and Short-Answer Questions generation.
"""

from typing import List, Optional
from pydantic import BaseModel, Field


# ── Flashcards ───────────────────────────────────────────────────
class FlashcardItem(BaseModel):
    front: str = Field(..., description="Concise question or prompt on the front")
    back: str = Field(..., description="Concise, correct answer or explanation on the back")
    topic: str = Field(default="General", description="Subject topic category for future weak-area tracking")


class GenerateFlashcardsRequest(BaseModel):
    document_id: Optional[str] = None
    file_id: Optional[str] = None

    @property
    def target_document_id(self) -> str:
        doc_id = self.document_id or self.file_id
        if not doc_id:
            raise ValueError("document_id (or file_id) is required.")
        return doc_id


class GenerateFlashcardsResponse(BaseModel):
    document_id: str
    flashcards: List[FlashcardItem]


# ── MCQs (Phase 2 Step 2) ─────────────────────────────────────────
class MCQItem(BaseModel):
    question: str = Field(..., description="The multiple choice question prompt")
    options: List[str] = Field(..., min_length=4, max_length=4, description="Exactly 4 options")
    correct_index: int = Field(..., ge=0, le=3, description="0-indexed position (0-3) of the correct answer")
    topic: str = Field(default="General", description="Topic label representing the tested concept")


class GenerateMCQRequest(BaseModel):
    document_id: Optional[str] = None
    file_id: Optional[str] = None

    @property
    def target_document_id(self) -> str:
        doc_id = self.document_id or self.file_id
        if not doc_id:
            raise ValueError("document_id (or file_id) is required.")
        return doc_id


class GenerateMCQResponse(BaseModel):
    document_id: str
    questions: List[MCQItem]

    # Alias for backwards compatibility
    @property
    def mcqs(self) -> List[MCQItem]:
        return self.questions


# ── Short-Answer Questions (Phase 2 Step 3) ───────────────────────
class ShortQuestionItem(BaseModel):
    question: str
    sample_answer: str
    key_points: List[str]
    topic: Optional[str] = Field(default="General", description="Topic category for analytics")


class GenerateShortQRequest(BaseModel):
    document_id: Optional[str] = None
    file_id: Optional[str] = None

    @property
    def target_document_id(self) -> str:
        doc_id = self.document_id or self.file_id
        if not doc_id:
            raise ValueError("document_id (or file_id) is required.")
        return doc_id


class GenerateShortQResponse(BaseModel):
    document_id: str
    questions: List[ShortQuestionItem]
