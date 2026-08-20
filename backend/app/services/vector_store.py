"""
app/services/vector_store.py
──────────────────────────────
ChromaDB client interface for storing and retrieving document embeddings.

WHY ChromaDB?
  - Open-source, fast, lightweight vector DB.
  - Automatically handles cosine similarity / distance calculation between query and stored text chunks.
"""

import chromadb
from chromadb.config import Settings as ChromaSettings
from typing import List, Dict, Any
from openai import OpenAI

from app.core.config import settings


class VectorStoreService:
    def __init__(self):
        # Connect to ChromaDB HTTP service or fallback to in-memory/local client
        try:
            self.client = chromadb.HttpClient(
                host=settings.CHROMA_HOST,
                port=settings.CHROMA_PORT,
            )
        except Exception:
            # Fallback to local persistent client if HTTP container not ready
            self.client = chromadb.PersistentClient(path="./chroma_db_data")

        self.openai_client = OpenAI(api_key=settings.OPENAI_API_KEY)

    def _get_embedding(self, text: str) -> List[float]:
        """Generate vector embedding for a string using OpenAI Embeddings API."""
        response = self.openai_client.embeddings.create(
            input=text,
            model=settings.EMBEDDING_MODEL,
        )
        return response.data[0].embedding

    def index_document(self, file_id: str, chunks: List[str]) -> int:
        """
        Indexes text chunks of a file into a ChromaDB collection dedicated to `file_id`.

        Returns:
            int: Number of chunks indexed.
        """
        if not chunks:
            return 0

        # Collection name per file_id (prefixed with file_)
        collection_name = f"file_{file_id.replace('-', '_')}"
        
        # Get or create collection
        collection = self.client.get_or_create_collection(
            name=collection_name,
            metadata={"file_id": file_id}
        )

        embeddings = []
        ids = []
        metadatas = []

        for i, chunk in enumerate(chunks):
            vector = self._get_embedding(chunk)
            embeddings.append(vector)
            ids.append(f"{file_id}_chunk_{i}")
            metadatas.append({"file_id": file_id, "chunk_index": i})

        collection.add(
            documents=chunks,
            embeddings=embeddings,
            ids=ids,
            metadatas=metadatas,
        )

        return len(chunks)

    def search_similar_chunks(self, file_id: str, query: str, top_k: int = 3) -> List[str]:
        """
        Searches ChromaDB for the top-k chunks most semantically relevant to `query`.
        """
        collection_name = f"file_{file_id.replace('-', '_')}"
        
        try:
            collection = self.client.get_collection(name=collection_name)
        except Exception:
            return []

        query_embedding = self._get_embedding(query)

        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
        )

        documents = results.get("documents", [[]])[0]
        return documents
