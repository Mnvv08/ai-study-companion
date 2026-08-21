"""
tests/test_notes.py
───────────────────
Unit tests for Structured Notes Generation endpoint (Prompt 6).
Tests ownership enforcement, defensive JSON parsing, and response formatting.
"""

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
from app.services.llm_client import LLMClientService, extract_and_parse_json

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
def student_user():
    db = TestingSessionLocal()
    user = User(
        id="user-notes-1",
        email="notes_student@university.edu",
        name="Study Student",
        hashed_password=get_password_hash("pass123"),
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
        id="user-notes-2",
        email="other_student@university.edu",
        name="Other Student",
        hashed_password=get_password_hash("pass123"),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    db.close()
    return user


@pytest.fixture
def auth_headers(student_user):
    token = create_access_token(data={"sub": student_user.id})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def other_auth_headers(other_user):
    token = create_access_token(data={"sub": other_user.id})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def sample_document(student_user):
    db = TestingSessionLocal()
    doc = Document(
        id="doc-os-200",
        user_id=student_user.id,
        filename="operating_systems_ch1.pdf",
        file_path="/tmp/os.pdf",
        file_size_bytes=8192,
        file_type="pdf",
        status="processed",
        extracted_text="A process is a program in execution. The process control block (PCB) stores registers, state, and PC.",
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
    db.close()
    return doc


def test_defensive_json_parser():
    """Verify that extract_and_parse_json correctly handles clean JSON, markdown-wrapped JSON, and noisy text."""
    # 1. Clean JSON
    clean = '{"title": "Test Notes", "sections": [], "key_terms": []}'
    parsed1 = extract_and_parse_json(clean)
    assert parsed1["title"] == "Test Notes"

    # 2. Markdown fenced JSON
    fenced = '```json\n{"title": "Fenced Notes", "sections": [{"heading": "Intro", "points": ["P1"]}], "key_terms": []}\n```'
    parsed2 = extract_and_parse_json(fenced)
    assert parsed2["title"] == "Fenced Notes"
    assert len(parsed2["sections"]) == 1

    # 3. JSON with leading/trailing commentary
    commentary = 'Here are the study notes you requested:\n{"title": "Notes with Text", "sections": [], "key_terms": []}\nHope this helps!'
    parsed3 = extract_and_parse_json(commentary)
    assert parsed3["title"] == "Notes with Text"


def test_generate_notes_unauthorized():
    """Verify that /notes/generate requires JWT authentication."""
    response = client.post("/notes/generate", json={"document_id": "doc-os-200"})
    assert response.status_code == 401


def test_generate_notes_other_user_document_404(other_auth_headers, sample_document):
    """Verify that a user cannot generate notes for another user's document (404)."""
    response = client.post(
        "/notes/generate",
        headers=other_auth_headers,
        json={"document_id": sample_document.id},
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "Document not found."


def test_generate_notes_success(auth_headers, sample_document, monkeypatch):
    """Verify structured notes generation returns valid schema (title, sections, key_terms)."""
    mock_notes = {
        "title": "Operating Systems: Processes",
        "sections": [
            {
                "heading": "Process Concept",
                "points": ["A process is an active program in execution.", "Contains text, data, heap, and stack."]
            }
        ],
        "key_terms": [
            {
                "term": "PCB",
                "definition": "Process Control Block containing CPU registers and process state."
            }
        ]
    }

    monkeypatch.setattr(
        LLMClientService,
        "generate_study_notes",
        lambda self, text, *args, **kwargs: mock_notes
    )

    response = client.post(
        "/notes/generate",
        headers=auth_headers,
        json={"document_id": sample_document.id},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["document_id"] == sample_document.id
    assert data["title"] == "Operating Systems: Processes"
    assert len(data["sections"]) == 1
    assert data["sections"][0]["heading"] == "Process Concept"
    assert len(data["key_terms"]) == 1
    assert data["key_terms"][0]["term"] == "PCB"
