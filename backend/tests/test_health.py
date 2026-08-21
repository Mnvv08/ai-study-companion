"""
tests/test_health.py
────────────────────
Unit tests for the health check and root endpoints.
Uses FastAPI TestClient (backed by httpx).
"""

from fastapi.testclient import TestClient
from app.main import app
from app.db.session import get_db

client = TestClient(app)


def test_root_endpoint():
    """Verify that the root endpoint returns a 200 and welcoming JSON message."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "message" in data
    assert "AI Study Companion" in data["message"]


def test_health_endpoint_mock_db():
    """
    Verify /api/v1/health endpoint with a mocked database session.
    Ensures the health check returns 'status: healthy' and 'database: connected'.
    """
    class MockDB:
        def execute(self, query):
            return 1

    # Override get_db dependency for isolated unit testing
    app.dependency_overrides[get_db] = lambda: MockDB()

    try:
        response = client.get("/api/v1/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["database"] == "connected"
        assert data["app"] == "AI Study Companion"
    finally:
        # Clean up dependency override
        app.dependency_overrides.clear()


def test_health_endpoint_mock_db_failure():
    """
    Verify /api/v1/health endpoint returns a 500 status code when database execution raises an exception.
    """
    class MockDBFailure:
        def execute(self, query):
            raise Exception("Connection Refused")

    app.dependency_overrides[get_db] = lambda: MockDBFailure()

    try:
        response = client.get("/api/v1/health")
        assert response.status_code == 500
        data = response.json()
        assert "Database connection error" in data["detail"]
    finally:
        app.dependency_overrides.clear()

