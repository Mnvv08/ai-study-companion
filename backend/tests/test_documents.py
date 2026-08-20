"""
tests/test_documents.py
───────────────────────
Unit tests for Document Upload + Validation (Prompt 2).
Tests edge validation (file type, size limits), status tracking, auth security, and DB persistence.
"""

import io
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.db.base import Base
from app.db.session import get_db
from app.core.security import create_access_token, get_password_hash
from app.models.user import User
from app.models.file import Document
from app.core.config import settings

# In-memory SQLite database for isolated test execution
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

client = TestClient(app)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(autouse=True)
def setup_database():
    Base.metadata.create_all(bind=engine)
    app.dependency_overrides[get_db] = override_get_db
    yield
    Base.metadata.drop_all(bind=engine)
    app.dependency_overrides.clear()


@pytest.fixture
def test_user():
    db = TestingSessionLocal()
    user = User(
        id="user-123-abc",
        email="student@university.edu",
        name="Alex Student",
        hashed_password=get_password_hash("securepass123"),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    db.close()
    return user


@pytest.fixture
def other_user():
    db = TestingSessionLocal()
    user = User(
        id="user-456-def",
        email="other@university.edu",
        name="Other Student",
        hashed_password=get_password_hash("securepass123"),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    db.close()
    return user


@pytest.fixture
def auth_headers(test_user):
    token = create_access_token(data={"sub": test_user.id})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def other_auth_headers(other_user):
    token = create_access_token(data={"sub": other_user.id})
    return {"Authorization": f"Bearer {token}"}


def test_upload_without_auth_fails():
    """Verify that document upload is protected and returns 401 without JWT."""
    pdf_content = b"%PDF-1.4 Fake PDF Content for testing"
    files = {"file": ("notes.pdf", io.BytesIO(pdf_content), "application/pdf")}
    response = client.post("/documents/upload", files=files)
    assert response.status_code == 401


def test_upload_non_pdf_rejected(auth_headers):
    """Verify that non-PDF files (e.g. .txt, .exe, .png) are rejected at the edge with 400."""
    txt_content = b"This is plain text, not a PDF."
    files = {"file": ("notes.txt", io.BytesIO(txt_content), "text/plain")}
    response = client.post("/documents/upload", headers=auth_headers, files=files)
    assert response.status_code == 400
    assert "Only PDF files are supported" in response.json()["detail"]


def test_upload_oversized_file_rejected(auth_headers, monkeypatch):
    """Verify that files exceeding the size limit are rejected with 413 Payload Too Large."""
    # Temporarily set max upload size to 1 MB for testing
    monkeypatch.setattr(settings, "MAX_UPLOAD_SIZE_MB", 1)
    
    # 1.5 MB payload
    large_content = b"0" * int(1.5 * 1024 * 1024)
    files = {"file": ("huge_lecture.pdf", io.BytesIO(large_content), "application/pdf")}
    response = client.post("/documents/upload", headers=auth_headers, files=files)
    assert response.status_code == 413
    assert "exceeds the maximum allowed limit" in response.json()["detail"]


def test_upload_valid_pdf_success(auth_headers, test_user):
    """Verify valid PDF upload returns 201 with document ID and status='pending'."""
    pdf_content = b"%PDF-1.4 sample lecture content on Algorithms"
    files = {"file": ("algorithms_lecture1.pdf", io.BytesIO(pdf_content), "application/pdf")}
    
    response = client.post("/documents/upload", headers=auth_headers, files=files)
    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert data["status"] == "pending"
    assert data["filename"] == "algorithms_lecture1.pdf"
    assert data["file_size_bytes"] == len(pdf_content)


def test_get_document_status(auth_headers, test_user):
    """Verify GET /documents/{id}/status returns current status for the owner."""
    # Seed a document directly
    db = TestingSessionLocal()
    doc = Document(
        id="doc-xyz-789",
        user_id=test_user.id,
        filename="db_lecture.pdf",
        file_path="/tmp/fake_db_lecture.pdf",
        file_size_bytes=1024,
        file_type="pdf",
        status="pending",
    )
    db.add(doc)
    db.commit()
    db.close()

    response = client.get("/documents/doc-xyz-789/status", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == "doc-xyz-789"
    assert data["status"] == "pending"
    assert data["filename"] == "db_lecture.pdf"


def test_get_document_status_unauthorized_user_gets_404(other_auth_headers, test_user):
    """Verify that another user attempting to query a document's status gets a 404 (multi-tenant security)."""
    db = TestingSessionLocal()
    doc = Document(
        id="doc-private-111",
        user_id=test_user.id,
        filename="secret_exam_review.pdf",
        file_path="/tmp/secret.pdf",
        file_size_bytes=512,
        file_type="pdf",
        status="pending",
    )
    db.add(doc)
    db.commit()
    db.close()

    # Query with other user's auth token
    response = client.get("/documents/doc-private-111/status", headers=other_auth_headers)
    assert response.status_code == 404
    assert response.json()["detail"] == "Document not found."
