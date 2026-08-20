"""
app/services/extractor.py
──────────────────────────
PDF text extraction service using PyMuPDF (fitz).

WHY PyMuPDF?
  - Extremely fast C-backed PDF parsing engine.
  - Extracts clean plain text preserving reading order.
  - Doesn't require external heavy dependencies like Tesseract/Java.
"""

import fitz  # PyMuPDF
import os


class TextExtractorService:
    @staticmethod
    def extract_text_from_pdf(file_path: str) -> str:
        """
        Reads a PDF file from file_path and extracts all text content.

        Raises:
            ValueError: If file doesn't exist, is corrupt, or contains no readable text.
        """
        if not os.path.exists(file_path):
            raise ValueError(f"File not found at path: {file_path}")

        try:
            doc = fitz.open(file_path)
            full_text = []

            for page_num in range(len(doc)):
                page = doc.load_page(page_num)
                text = page.get_text("text")
                if text and text.strip():
                    full_text.append(f"--- Page {page_num + 1} ---\n{text.strip()}")

            doc.close()

            extracted = "\n\n".join(full_text)
            if not extracted.strip():
                raise ValueError("PDF appears to be scanned or contains no extractable text.")

            return extracted

        except Exception as e:
            if isinstance(e, ValueError):
                raise e
            raise ValueError(f"Failed to parse PDF file: {str(e)}")
