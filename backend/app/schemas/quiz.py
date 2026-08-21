"""
app/schemas/quiz.py
───────────────────
Pydantic schemas for Quiz and Question operations.
"""

from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel, Field


class QuestionAttemptResponse(BaseModel):
    id: str = Field(..., description="Unique database ID for the question")
    quiz_id: str = Field(..., description="ID of the parent quiz")
    question_text: str = Field(..., description="The question prompt")
    options: Optional[List[str]] = Field(default=None, description="Plausible options (MCQ only)")
    topic_tag: str = Field(..., description="Topic classification label")

    class Config:
        from_attributes = True


class QuizAttemptResponse(BaseModel):
    id: str = Field(..., description="Unique database ID for the quiz")
    document_id: str = Field(..., description="ID of the document this quiz is based on")
    quiz_type: str = Field(..., description="Type of the quiz ('mcq' or 'short_answer')")
    created_at: datetime = Field(..., description="Timestamp when the quiz was generated")
    questions: List[QuestionAttemptResponse] = Field(..., description="List of questions for this quiz")

    class Config:
        from_attributes = True
