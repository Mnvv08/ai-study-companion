"""
tests/test_rate_limiting.py
───────────────────────────
Unit/integration tests for per-user rate limiting (Phase 8).
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
from app.core.rate_limiter import limiter

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
    # Explicitly enable rate limiter for rate limiting tests
    limiter.enabled = True
    # Reset storage to start with clean rate limit state
    limiter._limiter.storage.reset()
    yield
    # Disable after tests to avoid polluting other test suites
    limiter.enabled = False
    Base.metadata.drop_all(bind=engine)
    app.dependency_overrides.clear()


@pytest.fixture
def test_user():
    db = TestingSessionLocal()
    user = User(
        id="user-limiter-1",
        email="limiter@university.edu",
        name="Limiter Student",
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


def test_rate_limiting_exceeded_429(auth_headers):
    """Verify that making 21 requests to /analytics/recommendations triggers a 429 Rate Limit Exceeded."""
    # First 20 requests should pass successfully (or 200/404/etc, not 429)
    for i in range(20):
        response = client.get("/analytics/recommendations", headers=auth_headers)
        assert response.status_code != 429

    # The 21st request must trigger 429 Rate Limit Exceeded
    response = client.get("/analytics/recommendations", headers=auth_headers)
    assert response.status_code == 429
    assert "Rate limit exceeded" in response.json()["error"]
