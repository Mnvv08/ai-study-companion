"""
tests/test_short_answer.py
──────────────────────────
Unit tests for Short-Answer Question Generation endpoint (Phase 2).
Tests ownership enforcement, 1-3 sentence model answer schema formatting, topic tagging, and error handling.
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
from app.services.llm_client import LLMClientService

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
        id="user-sa-1",
        email="sa_student@university.edu",
        name="ShortAnswer Student",
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
        id="user-sa-2",
        email="other_sa@university.edu",
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
        id="doc-arch-501",
        user_id=student_user.id,
        filename="computer_architecture_pipelining.pdf",
        file_path="/tmp/arch.pdf",
        file_size_bytes=7168,
        file_type="pdf",
        status="processed",
        extracted_text="Pipelining is an implementation technique where multiple instructions are overlapped in execution. The three major pipeline hazards are structural hazards, data hazards, and control hazards.",
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
    db.close()
    return doc


def test_generate_short_answer_unauthorized():
    """Verify that /short-answer/generate requires JWT authentication."""
    response = client.post("/short-answer/generate", json={"document_id": "doc-arch-501"})
    assert response.status_code == 401


def test_generate_short_answer_other_user_document_404(other_auth_headers, sample_document):
    """Verify that requesting short-answer questions on another student's document returns 404."""
    response = client.post(
        "/short-answer/generate",
        headers=other_auth_headers,
        json={"document_id": sample_document.id},
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "Document not found."


def test_generate_short_answer_success(auth_headers, sample_document, monkeypatch):
    """Verify valid short-answer question generation returns questions with question, model_answer, and topic."""
    mock_questions = [
        {
            "question": "What is instruction pipelining in CPU design?",
            "model_answer": "Pipelining is an implementation technique in which multiple instructions are overlapped in execution to increase CPU instruction throughput.",
            "topic": "Pipelining Architecture"
        },
        {
            "question": "Name and briefly explain the three main types of pipeline hazards.",
            "model_answer": "The three hazards are structural hazards (hardware resource conflicts), data hazards (data dependencies between instructions), and control hazards (branching delays).",
            "topic": "Pipeline Hazards"
        }
    ]

    monkeypatch.setattr(
        LLMClientService,
        "generate_short_questions",
        lambda self, text_content: mock_questions
    )

    response = client.post(
        "/short-answer/generate",
        headers=auth_headers,
        json={"document_id": sample_document.id},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["document_id"] == sample_document.id
    assert len(data["questions"]) == 2
    
    first_q = data["questions"][0]
    assert "pipelining" in first_q["question"].lower()
    assert "instruction throughput" in first_q["model_answer"].lower()
    assert first_q["topic"] == "Pipelining Architecture"
