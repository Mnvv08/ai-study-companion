"""
tests/test_caching.py
─────────────────────
Unit tests for basic in-memory caching of study materials (Phase 8).
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
from app.core.cache import study_cache

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
    # Clean cache before and after test runs
    study_cache.clear()
    yield
    study_cache.clear()
    Base.metadata.drop_all(bind=engine)
    app.dependency_overrides.clear()


@pytest.fixture
def test_user():
    db = TestingSessionLocal()
    user = User(
        id="user-cache-1",
        email="cache@university.edu",
        name="Cache Student",
        hashed_password=get_password_hash("pass123"),
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
def sample_document(test_user):
    db = TestingSessionLocal()
    doc = Document(
        id="doc-cache-99",
        user_id=test_user.id,
        filename="caching_test.pdf",
        file_path="/tmp/cache.pdf",
        file_size_bytes=1024,
        file_type="pdf",
        status="processed",
        extracted_text="Caching stores temporary data in-memory for quick retrieval.",
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
    db.close()
    return doc


def test_notes_generation_caching_and_bypass(auth_headers, sample_document, monkeypatch):
    """Verify that notes endpoint caches LLM results and force_regenerate bypasses/invalidates it."""
    call_count = 0

    def mock_generate_study_notes(self, text, *args, **kwargs):
        nonlocal call_count
        call_count += 1
        return {
            "title": f"Notes Call {call_count}",
            "sections": [{"heading": "Cache Test", "points": [f"Point {call_count}"]}],
            "key_terms": []
        }

    monkeypatch.setattr(LLMClientService, "generate_study_notes", mock_generate_study_notes)

    # 1. First call - populates cache
    response1 = client.post(
        "/notes/generate",
        headers=auth_headers,
        json={"document_id": sample_document.id}
    )
    assert response1.status_code == 200
    assert response1.json()["title"] == "Notes Call 1"
    assert call_count == 1

    # 2. Second call - hits cache (call_count should remain 1)
    response2 = client.post(
        "/notes/generate",
        headers=auth_headers,
        json={"document_id": sample_document.id}
    )
    assert response2.status_code == 200
    assert response2.json()["title"] == "Notes Call 1"
    assert call_count == 1

    # 3. Third call - with force_regenerate=True bypasses cache (call_count becomes 2)
    response3 = client.post(
        "/notes/generate",
        headers=auth_headers,
        json={"document_id": sample_document.id, "force_regenerate": True}
    )
    assert response3.status_code == 200
    assert response3.json()["title"] == "Notes Call 2"
    assert call_count == 2
