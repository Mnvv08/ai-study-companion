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


class AnswerSubmitItem(BaseModel):
    question_id: str = Field(..., description="ID of the question being answered")
    student_answer: str = Field(..., description="Student's selected option index or short-answer text")


class QuizSubmitRequest(BaseModel):
    answers: List[AnswerSubmitItem] = Field(..., description="List of submitted answers for the quiz questions")


class QuestionFeedback(BaseModel):
    question_id: str = Field(..., description="ID of the question")
    question_text: str = Field(..., description="The original question prompt")
    student_answer: str = Field(..., description="The answer submitted by the student")
    correct_answer: str = Field(..., description="The correct option index or model answer")
    is_correct: bool = Field(..., description="True if the student's answer was graded correct")


class QuizSubmitResponse(BaseModel):
    attempt_id: str = Field(..., description="Unique database ID for this quiz attempt")
    quiz_id: str = Field(..., description="ID of the quiz attempted")
    score: float = Field(..., description="Score fraction from 0.0 to 1.0 (correct / total)")
    questions_count: int = Field(..., description="Total number of questions in the quiz")
    correct_count: int = Field(..., description="Number of questions answered correctly")
    feedback: List[QuestionFeedback] = Field(..., description="Per-question feedback details")

