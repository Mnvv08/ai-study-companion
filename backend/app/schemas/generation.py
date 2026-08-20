"""
app/schemas/generation.py
──────────────────────────
Pydantic request and response schemas for Flashcards, MCQs, and Short-Answer Questions.
"""

from pydantic import BaseModel, Field
from typing import List


# ── Flashcards ───────────────────────────────────────────────────
class FlashcardItem(BaseModel):
    front: str = Field(..., description="Question, prompt, or term on the front of the flashcard")
    back: str = Field(..., description="Answer, explanation, or definition on the back")


class GenerateFlashcardsRequest(BaseModel):
    file_id: str
    count: int = Field(default=10, ge=3, le=20, description="Number of flashcards to generate (3-20)")


class GenerateFlashcardsResponse(BaseModel):
    file_id: str
    flashcards: List[FlashcardItem]


# ── MCQs ─────────────────────────────────────────────────────────
class MCQItem(BaseModel):
    id: int
    question: str
    options: List[str] = Field(..., min_length=4, max_length=4, description="Exactly 4 multiple choice options")
    correct_answer: str = Field(..., description="Must exactly match one of the 4 options")
    explanation: str = Field(..., description="Detailed explanation of why this answer is correct")


class GenerateMCQRequest(BaseModel):
    file_id: str
    count: int = Field(default=5, ge=3, le=15, description="Number of MCQs to generate (3-15)")


class GenerateMCQResponse(BaseModel):
    file_id: str
    mcqs: List[MCQItem]


# ── Short-Answer Questions ────────────────────────────────────────
class ShortQuestionItem(BaseModel):
    id: int
    question: str
    sample_answer: str
    key_points: List[str] = Field(..., description="Key bullet points required to get full marks on this question")


class GenerateShortQRequest(BaseModel):
    file_id: str
    count: int = Field(default=5, ge=2, le=10, description="Number of short-answer questions to generate (2-10)")


class GenerateShortQResponse(BaseModel):
    file_id: str
    questions: List[ShortQuestionItem]
