"""
app/api/v1/rag.py
─────────────────
RAG (Retrieval-Augmented Generation) Question Answering endpoints.

Workflow:
  1. Authenticate user and verify document ownership (404 on mismatch).
  2. Embed user question and retrieve top semantically relevant chunks from ChromaDB
     (strictly filtered by user_id AND document_id).
  3. Format prompt with retrieved context chunks.
  4. Query LLM to generate grounded, fact-checked answer.
"""

import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.file import Document
from app.schemas.rag import AskQuestionRequest, AskQuestionResponse, AskMultiQuestionRequest, AskMultiQuestionResponse
from app.services.chunker import TextChunkerService
from app.services.vector_store import VectorStoreService
from app.services.llm_client import LLMClientService

logger = logging.getLogger(__name__)

router = APIRouter(tags=["RAG Q&A"])


@router.post(
    "/qa/ask",
    response_model=AskQuestionResponse,
    summary="Ask a question about an uploaded study document (RAG Q&A)",
)
@router.post(
    "/rag/ask",
    response_model=AskQuestionResponse,
    include_in_schema=False,
)
def ask_question(
    request: AskQuestionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    RAG-backed Q&A endpoint.

    Steps:
      1. Validates document existence and ensures requesting user is the owner (404 otherwise).
      2. Retrieves top 3-5 relevant chunks from ChromaDB filtered by user_id and document_id.
      3. Calls LLM with strict grounding prompt.
      4. Returns clear, exam-relevant answer.
     """
    # ── 1. Resolve Document ID & Verify Ownership ─────────────────
    try:
        doc_id = request.target_document_id
    except ValueError as val_err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(val_err),
        )

    db_doc = (
        db.query(Document)
        .filter(Document.id == doc_id, Document.user_id == current_user.id)
        .first()
    )
    if not db_doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found.",
        )

    # ── 2. Retrieve Relevant Context from Vector Store ─────────────
    vector_service = VectorStoreService()
    relevant_chunks = []

    try:
        relevant_chunks = vector_service.search_similar_chunks(
            user_id=current_user.id,
            document_id=db_doc.id,
            query=request.question,
            top_k=4,
        )
    except Exception as search_err:
        logger.warning(f"ChromaDB search encountered an issue: {search_err}")

    # If vector store has no chunks indexed yet (e.g. initial upload), index on the fly
    if not relevant_chunks and db_doc.extracted_text:
        try:
            chunks = TextChunkerService.chunk_text(
                db_doc.extracted_text, chunk_size=500, chunk_overlap=50
            )
            vector_service.add_document_chunks(
                user_id=current_user.id, document_id=db_doc.id, chunks=chunks
            )
            relevant_chunks = vector_service.search_similar_chunks(
                user_id=current_user.id,
                document_id=db_doc.id,
                query=request.question,
                top_k=4,
            )
        except Exception as idx_err:
            logger.error(f"On-the-fly indexing failed: {idx_err}")

    # Handle case where no relevant chunks can be found
    if not relevant_chunks:
        return AskQuestionResponse(
            document_id=db_doc.id,
            question=request.question,
            answer="I couldn't find this in your uploaded material.",
            sources_used=[],
        )

    # ── 3. Call LLM for Grounded Answer ────────────────────────────
    llm_service = LLMClientService()
    try:
        answer = llm_service.answer_question_with_context(
            question=request.question,
            context_chunks=relevant_chunks,
        )
        return AskQuestionResponse(
            document_id=db_doc.id,
            question=request.question,
            answer=answer,
            sources_used=relevant_chunks,
        )
    except RuntimeError as llm_err:
        logger.error(f"LLM API error during Q&A: {llm_err}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"AI service temporarily unavailable: {str(llm_err)}",
        )
    except Exception as general_err:
        logger.error(f"Unexpected error in Q&A endpoint: {general_err}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while generating the answer. Please try again.",
        )


@router.post(
    "/qa/ask-multi",
    response_model=AskMultiQuestionResponse,
    summary="Ask a question across multiple uploaded study documents (RAG Q&A)",
)
def ask_question_multi(
    request: AskMultiQuestionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Multi-document RAG Q&A endpoint.
    Retrieves up to 2 top chunks per document to maintain a balanced context.
    """
    # 1. Verify that all document IDs belong to the current user (404/403 if any don't)
    docs = (
        db.query(Document)
        .filter(Document.id.in_(request.document_ids), Document.user_id == current_user.id)
        .all()
    )

    if len(docs) != len(set(request.document_ids)):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="One or more documents not found or unauthorized.",
        )

    # 2. Retrieve top 2 relevant chunks per document to avoid context overflow and maintain balance
    vector_service = VectorStoreService()
    combined_chunks = []

    for doc in docs:
        chunks = []
        try:
            chunks = vector_service.search_similar_chunks(
                user_id=current_user.id,
                document_id=doc.id,
                query=request.question,
                top_k=2,
            )
        except Exception as search_err:
            logger.warning(f"ChromaDB search encountered an issue for document {doc.id}: {search_err}")

        # On-the-fly indexing fallback
        if not chunks and doc.extracted_text:
            try:
                doc_chunks = TextChunkerService.chunk_text(
                    doc.extracted_text, chunk_size=500, chunk_overlap=50
                )
                vector_service.add_document_chunks(
                    user_id=current_user.id, document_id=doc.id, chunks=doc_chunks
                )
                chunks = vector_service.search_similar_chunks(
                    user_id=current_user.id,
                    document_id=doc.id,
                    query=request.question,
                    top_k=2,
                )
            except Exception as idx_err:
                logger.error(f"On-the-fly indexing failed for document {doc.id}: {idx_err}")

        combined_chunks.extend(chunks)

    # Handle case where no context chunks are found across all documents
    if not combined_chunks:
        return AskMultiQuestionResponse(
            document_ids=[doc.id for doc in docs],
            question=request.question,
            answer="I couldn't find this in your uploaded material.",
            sources_used=[],
        )

    # 3. Call LLM for Grounded Answer
    llm_service = LLMClientService()
    try:
        answer = llm_service.answer_question_with_context(
            question=request.question,
            context_chunks=combined_chunks,
        )
        return AskMultiQuestionResponse(
            document_ids=[doc.id for doc in docs],
            question=request.question,
            answer=answer,
            sources_used=combined_chunks,
        )
    except RuntimeError as llm_err:
        logger.error(f"LLM API error during Q&A: {llm_err}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"AI service temporarily unavailable: {str(llm_err)}",
        )
    except Exception as general_err:
        logger.error(f"Unexpected error in multi Q&A endpoint: {general_err}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while generating the answer. Please try again.",
        )

