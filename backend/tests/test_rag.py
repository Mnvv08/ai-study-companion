"""
tests/test_rag.py
─────────────────
Unit tests for RAG Q&A endpoint (Prompt 5).
Tests document ownership checks, context retrieval from vector store, and grounded LLM answers.
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
from app.services.vector_store import VectorStoreService
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
        id="user-rag-1",
        email="student@rag.edu",
        name="Study User",
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
        id="user-rag-2",
        email="other@rag.edu",
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
        id="doc-algo-101",
        user_id=student_user.id,
        filename="dijkstra_notes.pdf",
        file_path="/tmp/dijkstra.pdf",
        file_size_bytes=4096,
        file_type="pdf",
        status="processed",
        extracted_text="Dijkstra's algorithm finds the shortest paths from a source node to all other nodes in a graph with non-negative edge weights.",
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
    db.close()
    return doc


def test_ask_question_unauthorized_fails():
    """Verify that /qa/ask requires a valid JWT."""
    response = client.post("/qa/ask", json={"document_id": "doc-algo-101", "question": "What is Dijkstra?"})
    assert response.status_code == 401


def test_ask_question_other_user_document_returns_404(other_auth_headers, sample_document):
    """Verify that asking questions on another student's document returns 404 (multi-tenant security)."""
    response = client.post(
        "/qa/ask",
        headers=other_auth_headers,
        json={"document_id": sample_document.id, "question": "What is the time complexity?"},
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "Document not found."


def test_ask_question_success(auth_headers, sample_document, monkeypatch):
    """Verify that /qa/ask retrieves relevant chunks and calls LLM client for grounded response."""
    # Mock vector search
    monkeypatch.setattr(
        VectorStoreService,
        "search_similar_chunks",
        lambda self, user_id, document_id, query, top_k=4: [
            "Dijkstra's algorithm finds the shortest paths from a source node to all other nodes with non-negative edge weights."
        ]
    )

    # Mock LLM answering
    monkeypatch.setattr(
        LLMClientService,
        "answer_question_with_context",
        lambda self, question, context_chunks: "Dijkstra's algorithm is an algorithm used to find the shortest path in non-negative weighted graphs."
    )

    response = client.post(
        "/qa/ask",
        headers=auth_headers,
        json={"document_id": sample_document.id, "question": "What does Dijkstra algorithm do?"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["document_id"] == sample_document.id
    assert "Dijkstra" in data["answer"]
    assert len(data["sources_used"]) > 0


def test_ask_question_no_context_returns_clean_fallback(auth_headers, sample_document, monkeypatch):
    """Verify that when no chunks are found, it returns the standard fallback message without error."""
    monkeypatch.setattr(
        VectorStoreService,
        "search_similar_chunks",
        lambda self, user_id, document_id, query, top_k=4: []
    )
    # Also document has no extracted text
    db = TestingSessionLocal()
    doc = db.query(Document).filter(Document.id == sample_document.id).first()
    doc.extracted_text = None
    db.commit()
    db.close()

    response = client.post(
        "/qa/ask",
        headers=auth_headers,
        json={"document_id": sample_document.id, "question": "What is quantum entanglement?"},
    )

    assert response.status_code == 200
    data = response.json()
    assert "I couldn't find this in your uploaded material" in data["answer"]


def test_ask_question_multi_unauthorized():
    """Verify that /qa/ask-multi requires valid JWT authorization."""
    response = client.post("/qa/ask-multi", json={"document_ids": ["doc-1"], "question": "What is Dijkstra?"})
    assert response.status_code == 401


def test_ask_question_multi_not_found(auth_headers, sample_document):
    """Verify that /qa/ask-multi returns 404 if any document ID is invalid or belongs to another user."""
    # Try querying sample_document and another fake one
    response = client.post(
        "/qa/ask-multi",
        headers=auth_headers,
        json={"document_ids": [sample_document.id, "fake-doc-999"], "question": "What is Dijkstra?"}
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "One or more documents not found or unauthorized."


def test_ask_question_multi_success(auth_headers, student_user, sample_document, monkeypatch):
    """Verify that /qa/ask-multi retrieves chunks from all documents and returns the answer."""
    db = TestingSessionLocal()
    # Create a second document for the student
    doc2 = Document(
        id="doc-bellman-202",
        user_id=student_user.id,
        filename="bellman_ford.pdf",
        file_path="/tmp/bellman.pdf",
        file_size_bytes=2048,
        file_type="pdf",
        status="processed",
        extracted_text="Bellman-Ford algorithm finds shortest paths in a graph and supports negative edge weights.",
    )
    db.add(doc2)
    db.commit()
    db.refresh(doc2)
    db.close()

    # Mock vector store query to return different context chunks for each document
    def mock_search_similar_chunks(self, user_id, document_id, query, top_k=2):
        if document_id == "doc-algo-101":
            return ["Dijkstra matches non-negative edge weights."]
        elif document_id == "doc-bellman-202":
            return ["Bellman-Ford matches negative edge weights."]
        return []

    monkeypatch.setattr(
        VectorStoreService,
        "search_similar_chunks",
        mock_search_similar_chunks
    )

    # Mock LLM response
    monkeypatch.setattr(
        LLMClientService,
        "answer_question_with_context",
        lambda self, question, context_chunks: "Dijkstra handles non-negative edge weights, while Bellman-Ford supports negative weights."
    )

    payload = {
        "document_ids": [sample_document.id, "doc-bellman-202"],
        "question": "Compare Dijkstra and Bellman-Ford algorithms."
    }

    response = client.post(
        "/qa/ask-multi",
        headers=auth_headers,
        json=payload
    )

    assert response.status_code == 200
    data = response.json()
    assert len(data["document_ids"]) == 2
    assert "doc-algo-101" in data["document_ids"]
    assert "doc-bellman-202" in data["document_ids"]
    assert "negative" in data["answer"]
    assert len(data["sources_used"]) == 2
    assert "Dijkstra matches non-negative edge weights." in data["sources_used"]
    assert "Bellman-Ford matches negative edge weights." in data["sources_used"]

