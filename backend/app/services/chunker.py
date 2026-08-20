"""
app/services/chunker.py
────────────────────────
Text chunking service using langchain-text-splitters.

WHY chunk with overlap?
  - chunk_size=1000 characters (~200 words): optimal granularity for retrieving relevant paragraphs.
  - chunk_overlap=150 characters: preserves context across split boundaries so a concept split halfway isn't lost.
"""

from langchain_text_splitters import RecursiveCharacterTextSplitter
from typing import List


class TextChunkerService:
    @staticmethod
    def chunk_text(
        text: str, chunk_size: int = 1000, chunk_overlap: int = 150
    ) -> List[str]:
        """
        Splits raw text into manageable overlapping chunks.
        """
        if not text or not text.strip():
            return []

        splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=["\n\n", "\n", " ", ""],
        )

        chunks = splitter.split_text(text)
        return [c.strip() for c in chunks if c.strip()]
