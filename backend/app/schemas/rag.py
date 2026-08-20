"""
app/schemas/rag.py
──────────────────
Pydantic schemas for RAG Q&A and Notes generation.
"""

from pydantic import BaseModel, Field
from typing import List, Optional


class AskQuestionRequest(BaseModel):
    document_id: Optional[str] = None
    file_id: Optional[str] = None
    question: str = Field(..., min_length=2, max_length=1000)

    @property
    def target_document_id(self) -> str:
        doc_id = self.document_id or self.file_id
        if not doc_id:
            raise ValueError("document_id (or file_id) is required.")
        return doc_id


class AskQuestionResponse(BaseModel):
    document_id: str
    question: str
    answer: str
    sources_used: List[str] = Field(default_factory=list)


class GenerateNotesRequest(BaseModel):
    document_id: Optional[str] = None
    file_id: Optional[str] = None

    @property
    def target_document_id(self) -> str:
        doc_id = self.document_id or self.file_id
        if not doc_id:
            raise ValueError("document_id (or file_id) is required.")
        return doc_id


class NoteSection(BaseModel):
    heading: str
    points: List[str]


class KeyTerm(BaseModel):
    term: str
    definition: str


class GenerateNotesResponse(BaseModel):
    document_id: str
    title: str
    sections: List[NoteSection]
    key_terms: List[KeyTerm]
