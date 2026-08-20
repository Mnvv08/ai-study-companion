"""
tests/test_extraction.py
────────────────────────
Unit tests for text extraction service (Prompt 3).
Tests layout-aware PDF text extraction and graceful error handling on corrupt/unreadable files.
"""

import os
import pytest
from app.services.extraction import extract_text_from_pdf


def test_extract_text_nonexistent_file():
    """Verify that extract_text_from_pdf raises ValueError when file does not exist."""
    with pytest.raises(ValueError, match="File not found"):
        extract_text_from_pdf("/tmp/non_existent_study_file_12345.pdf")


def test_extract_text_corrupt_pdf(tmp_path):
    """Verify that corrupt or unreadable PDF files raise a descriptive ValueError rather than crashing."""
    corrupt_file = tmp_path / "corrupt.pdf"
    corrupt_file.write_bytes(b"%PDF-1.4 THIS IS JUNK DATA NOT A REAL PDF STREAM")
    
    with pytest.raises(ValueError) as exc_info:
        extract_text_from_pdf(str(corrupt_file))
    
    assert "Corrupt or unreadable PDF" in str(exc_info.value) or "no extractable text" in str(exc_info.value)
