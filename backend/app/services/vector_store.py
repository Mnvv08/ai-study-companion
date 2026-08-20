"""
app/services/vector_store.py
──────────────────────────────
ChromaDB client wrapper for storing and querying document embeddings.

Security & Multi-Tenancy:
  Every chunk is tagged with `user_id` and `document_id` in its metadata.
  All similarity queries strictly enforce filtering by BOTH `user_id` and `document_id`
  to guarantee tenant data isolation.
"""

import logging
from typing import List, Dict, Any
import chromadb
from openai import OpenAI

from app.core.config import settings

logger = logging.getLogger(__name__)


class VectorStoreService:
    def __init__(self):
        """Initializes ChromaDB client and OpenAI embeddings client."""
        try:
            # Connect to ChromaDB HTTP container
            self.client = chromadb.HttpClient(
                host=settings.CHROMA_HOST,
                port=settings.CHROMA_PORT,
            )
            # Test connection
            self.client.heartbeat()
        except Exception as e:
            logger.warning(f"ChromaDB HttpClient unavailable ({e}), falling back to PersistentClient")
            self.client = chromadb.PersistentClient(path="./chroma_db_data")

        self.openai_client = OpenAI(api_key=settings.OPENAI_API_KEY)
        self.collection_name = "study_documents"

    def _get_or_create_collection(self):
        """Get or create the unified study_documents collection."""
        return self.client.get_or_create_collection(
            name=self.collection_name,
            metadata={"hnsw:space": "cosine"},
        )

    def _get_embedding(self, text: str) -> List[float]:
        """Generates embedding vector using OpenAI Embeddings API."""
        try:
            response = self.openai_client.embeddings.create(
                input=text,
                model=settings.EMBEDDING_MODEL,
            )
            return response.data[0].embedding
        except Exception as err:
            logger.error(f"OpenAI embedding generation failed: {err}")
            raise RuntimeError(f"Embedding generation failed: {str(err)}")

    def add_document_chunks(
        self, user_id: str, document_id: str, chunks: List[str]
    ) -> int:
        """
        Embeds and stores text chunks for a document into ChromaDB.
        Tags every chunk with user_id and document_id metadata for strict tenant isolation.
        """
        if not chunks:
            return 0

        collection = self._get_or_create_collection()
        embeddings = []
        ids = []
        metadatas = []
        clean_chunks = []

        for idx, chunk in enumerate(chunks):
            text = chunk.strip()
            if not text:
                continue
            
            vector = self._get_embedding(text)
            embeddings.append(vector)
            ids.append(f"{document_id}_chunk_{idx}")
            metadatas.append({
                "user_id": user_id,
                "document_id": document_id,
                "chunk_index": idx,
            })
            clean_chunks.append(text)

        if not clean_chunks:
            return 0

        collection.upsert(
            documents=clean_chunks,
            embeddings=embeddings,
            ids=ids,
            metadatas=metadatas,
        )
        logger.info(f"Indexed {len(clean_chunks)} chunks for document {document_id}")
        return len(clean_chunks)

    def search_similar_chunks(
        self, user_id: str, document_id: str, query: str, top_k: int = 4
    ) -> List[str]:
        """
        Searches ChromaDB for top-k semantically similar chunks.
        Strictly filters by BOTH user_id and document_id to prevent data leakage.
        """
        collection = self._get_or_create_collection()
        query_embedding = self._get_embedding(query)

        try:
            # Filter by both user_id and document_id
            results = collection.query(
                query_embeddings=[query_embedding],
                n_results=top_k,
                where={
                    "$and": [
                        {"user_id": {"$eq": user_id}},
                        {"document_id": {"$eq": document_id}},
                    ]
                },
            )

            documents = results.get("documents", [[]])[0]
            return [doc for doc in documents if doc]
        except Exception as query_err:
            logger.error(f"ChromaDB search failed: {query_err}")
            return []

    def get_document_chunks(
        self, user_id: str, document_id: str, max_chunks: int = 50
    ) -> List[str]:
        """
        Retrieves all stored text chunks for a document belonging to user_id.
        Sorted by chunk_index to reconstruct natural document reading flow.
        """
        collection = self._get_or_create_collection()
        try:
            results = collection.get(
                where={
                    "$and": [
                        {"user_id": {"$eq": user_id}},
                        {"document_id": {"$eq": document_id}},
                    ]
                },
                include=["documents", "metadatas"],
                limit=max_chunks,
            )
            documents = results.get("documents", [])
            metadatas = results.get("metadatas", [])
            if not documents:
                return []

            # Re-order chunks by chunk_index
            combined = sorted(
                zip(documents, metadatas),
                key=lambda x: x[1].get("chunk_index", 0) if x[1] else 0,
            )
            return [doc for doc, _ in combined if doc]
        except Exception as get_err:
            logger.error(f"Failed to retrieve chunks for document {document_id}: {get_err}")
            return []
