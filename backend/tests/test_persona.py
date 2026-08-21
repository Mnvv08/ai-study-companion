"""
tests/test_persona.py
─────────────────────
Unit/integration tests for toggleable Hinglish student-mentor persona (Phase 7).
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
def test_user():
    db = TestingSessionLocal()
    user = User(
        id="user-persona-1",
        email="persona_student@university.edu",
        name="Persona Student",
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


def test_get_settings_unauthorized():
    """Verify that settings endpoint requires JWT authorization."""
    response = client.get("/users/me/settings")
    assert response.status_code == 401


def test_get_and_patch_settings_success(auth_headers, test_user):
    """Verify getting default settings and patching persona_mode toggles correctly."""
    # 1. GET settings (should be False by default)
    response = client.get("/users/me/settings", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["persona_mode"] is False

    # 2. PATCH settings to True
    patch_response = client.patch(
        "/users/me/settings",
        headers=auth_headers,
        json={"persona_mode": True}
    )
    assert patch_response.status_code == 200
    assert patch_response.json()["persona_mode"] is True

    # 3. Verify in DB
    db = TestingSessionLocal()
    db_user = db.query(User).filter(User.id == test_user.id).first()
    assert db_user.persona_mode is True
    db.close()

    # 4. PATCH settings back to False
    patch_response_false = client.patch(
        "/users/me/settings",
        headers=auth_headers,
        json={"persona_mode": False}
    )
    assert patch_response_false.status_code == 200
    assert patch_response_false.json()["persona_mode"] is False


def test_persona_mode_system_prompt_wrapping():
    """Verify that _get_system_prompt appends persona addition text only when persona_mode is enabled."""
    llm_service = LLMClientService()
    base_prompt = "You are a helpful assistant."

    # Disabled
    prompt_disabled = llm_service._get_system_prompt(base_prompt, persona_mode=False)
    assert prompt_disabled == base_prompt

    # Enabled
    prompt_enabled = llm_service._get_system_prompt(base_prompt, persona_mode=True)
    assert base_prompt in prompt_enabled
    assert "Hinglish (Hindi-English mix)" in prompt_enabled
