"""
tests/test_mcqs.py
──────────────────
Unit tests for MCQ Generation endpoint (Phase 2).
Tests ownership enforcement, 4-option validation, correct_index (0-3) range checking,
and dropping of malformed questions.
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
        id="user-mcq-1",
        email="mcq_student@university.edu",
        name="MCQ Student",
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
        id="user-mcq-2",
        email="other_mcq@university.edu",
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
        id="doc-db-401",
        user_id=student_user.id,
        filename="dbms_normalization.pdf",
        file_path="/tmp/dbms.pdf",
        file_size_bytes=5120,
        file_type="pdf",
        status="processed",
        extracted_text="First Normal Form (1NF) requires atomic attribute values. 2NF removes partial functional dependencies. 3NF removes transitive dependencies.",
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
    db.close()
    return doc


def test_generate_mcqs_unauthorized():
    """Verify that /mcqs/generate requires JWT authentication."""
    response = client.post("/mcqs/generate", json={"document_id": "doc-db-401"})
    assert response.status_code == 401


def test_generate_mcqs_other_user_document_404(other_auth_headers, sample_document):
    """Verify that requesting MCQs on another student's document returns 404."""
    response = client.post(
        "/mcqs/generate",
        headers=other_auth_headers,
        json={"document_id": sample_document.id},
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "Document not found."


def test_generate_mcqs_success(auth_headers, sample_document, monkeypatch):
    """Verify valid MCQ generation returns questions with 4 options, correct_index in 0..3, and topic."""
    mock_mcqs = [
        {
            "question": "What is the primary requirement of First Normal Form (1NF)?",
            "options": [
                "Atomic attribute values",
                "No transitive dependencies",
                "No partial dependencies",
                "Every determinant is a candidate key"
            ],
            "correct_index": 0,
            "topic": "1NF Normalization"
        },
        {
            "question": "Which dependency is eliminated in Third Normal Form (3NF)?",
            "options": [
                "Partial dependency",
                "Transitive dependency",
                "Multi-valued dependency",
                "Join dependency"
            ],
            "correct_index": 1,
            "topic": "3NF Normalization"
        }
    ]

    monkeypatch.setattr(
        LLMClientService,
        "generate_mcqs",
        lambda self, text_content, *args, **kwargs: mock_mcqs
    )

    response = client.post(
        "/mcqs/generate",
        headers=auth_headers,
        json={"document_id": sample_document.id},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["document_id"] == sample_document.id
    assert len(data["questions"]) == 2
    
    first_q = data["questions"][0]
    assert len(first_q["options"]) == 4
    assert first_q["correct_index"] == 0
    assert first_q["topic"] == "1NF Normalization"


def test_generate_mcqs_drops_malformed_items(monkeypatch):
    """Verify that generate_mcqs drops items with != 4 options or correct_index out of bounds."""
    llm_service = LLMClientService()
    
    # Mock extract_and_parse_json to return 1 valid question and 3 malformed ones
    mock_raw_output = {
        "questions": [
            {
                "question": "Valid Question?",
                "options": ["A", "B", "C", "D"],
                "correct_index": 2,
                "topic": "Valid Topic"
            },
            {
                "question": "Malformed: Only 3 options",
                "options": ["A", "B", "C"],
                "correct_index": 1,
                "topic": "Bad Options"
            },
            {
                "question": "Malformed: correct_index is 4 (out of 0-3 range)",
                "options": ["A", "B", "C", "D"],
                "correct_index": 4,
                "topic": "Bad Index"
            },
            {
                "question": "Malformed: correct_index is negative",
                "options": ["A", "B", "C", "D"],
                "correct_index": -1,
                "topic": "Negative Index"
            }
        ]
    }

    monkeypatch.setattr(
        "app.services.llm_client.extract_and_parse_json",
        lambda raw: mock_raw_output
    )

    class MockChatCompletions:
        def create(self, **kwargs):
            class Choice:
                class Msg:
                    content = "{}"
                message = Msg()
            class Resp:
                choices = [Choice()]
            return Resp()

    monkeypatch.setattr(llm_service.client.chat, "completions", MockChatCompletions())

    clean_mcqs = llm_service.generate_mcqs("sample study text")
    # Only the 1 valid question should survive
    assert len(clean_mcqs) == 1
    assert clean_mcqs[0]["question"] == "Valid Question?"
    assert clean_mcqs[0]["correct_index"] == 2
