"""
tests/test_flashcards.py
────────────────────────
Unit tests for Flashcard Generation endpoint (Phase 2).
Tests ownership verification, topic tagging, active-recall schema formatting, and auth protection.
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
        id="user-fc-1",
        email="fc_student@university.edu",
        name="Flashcard Student",
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
        id="user-fc-2",
        email="other_fc@university.edu",
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
        id="doc-networks-301",
        user_id=student_user.id,
        filename="computer_networks_osi.pdf",
        file_path="/tmp/networks.pdf",
        file_size_bytes=6144,
        file_type="pdf",
        status="processed",
        extracted_text="The OSI model has 7 layers. Layer 3 is the Network layer which handles routing via IP addresses.",
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
    db.close()
    return doc


def test_generate_flashcards_unauthorized():
    """Verify that /flashcards/generate requires JWT authentication."""
    response = client.post("/flashcards/generate", json={"document_id": "doc-networks-301"})
    assert response.status_code == 401


def test_generate_flashcards_other_user_document_404(other_auth_headers, sample_document):
    """Verify that requesting flashcards on another user's document returns 404."""
    response = client.post(
        "/flashcards/generate",
        headers=other_auth_headers,
        json={"document_id": sample_document.id},
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "Document not found."


def test_generate_flashcards_success(auth_headers, sample_document, monkeypatch):
    """Verify that flashcard generation returns a list of items with front, back, and topic fields."""
    mock_cards = [
        {
            "front": "How many layers are in the OSI model?",
            "back": "7 layers.",
            "topic": "OSI Model Architecture"
        },
        {
            "front": "What is the primary function of OSI Layer 3 (Network Layer)?",
            "back": "Routing and logical IP addressing.",
            "topic": "Network Layer"
        }
    ]

    monkeypatch.setattr(
        LLMClientService,
        "generate_flashcards",
        lambda self, text_content: mock_cards
    )

    response = client.post(
        "/flashcards/generate",
        headers=auth_headers,
        json={"document_id": sample_document.id},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["document_id"] == sample_document.id
    assert len(data["flashcards"]) == 2
    assert data["flashcards"][0]["front"] == "How many layers are in the OSI model?"
    assert data["flashcards"][0]["back"] == "7 layers."
    assert data["flashcards"][0]["topic"] == "OSI Model Architecture"
