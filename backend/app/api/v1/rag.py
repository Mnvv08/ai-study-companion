"""
app/api/v1/rag.py
─────────────────
Endpoint for RAG-based Q&A (/ask).
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.file import UploadedFile
from app.schemas.rag import AskQuestionRequest, AskQuestionResponse
from app.services.chunker import TextChunkerService
from app.services.vector_store import VectorStoreService
from app.services.llm_client import LLMClientService

router = APIRouter(tags=["RAG Q&A"])


@router.post("/ask", response_model=AskQuestionResponse)
def ask_question(
    request: AskQuestionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    RAG-backed Q&A endpoint.
    Retrieves relevant text chunks from vector store and uses LLM to answer.
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
            status_code=400, detail="File has no extracted text available for Q&A."
        )

    vector_service = VectorStoreService()

    # Step 1: Query ChromaDB for top 3 matching chunks
    relevant_chunks = vector_service.search_similar_chunks(
        file_id=db_file.id, query=request.question, top_k=3
    )

    # If document hasn't been indexed into ChromaDB yet, index it on the fly!
    if not relevant_chunks:
        chunks = TextChunkerService.chunk_text(db_file.extracted_text)
        vector_service.index_document(file_id=db_file.id, chunks=chunks)
        # Search again after indexing
        relevant_chunks = vector_service.search_similar_chunks(
            file_id=db_file.id, query=request.question, top_k=3
        )

    # Fallback to direct raw text excerpt if still empty
    if not relevant_chunks:
        relevant_chunks = [db_file.extracted_text[:2000]]

    # Step 2: Pass retrieved context and question to LLM
    llm_service = LLMClientService()
    try:
        answer = llm_service.answer_question_with_context(
            question=request.question, context_chunks=relevant_chunks
        )
        return AskQuestionResponse(
            question=request.question,
            answer=answer,
            sources_used=relevant_chunks,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to answer question: {str(e)}",
        )
