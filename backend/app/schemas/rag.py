"""
app/schemas/rag.py
──────────────────
Pydantic schemas for RAG Q&A and Notes generation.
"""

from pydantic import BaseModel, Field
from typing import List, Dict, Any


class AskQuestionRequest(BaseModel):
    file_id: str
    question: str = Field(..., min_length=3, max_length=500)


class AskQuestionResponse(BaseModel):
    question: str
    answer: str
    sources_used: List[str]


class GenerateNotesRequest(BaseModel):
    file_id: str


class NoteSection(BaseModel):
    heading: str
    points: List[str]


class KeyTerm(BaseModel):
    term: str
    definition: str


class GenerateNotesResponse(BaseModel):
    file_id: str
    title: str
    sections: List[NoteSection]
    key_terms: List[KeyTerm]
