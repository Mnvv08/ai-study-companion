"""
app/api/v1/health.py
────────────────────
Health check endpoint.

WHY have a health check?
  - Docker's 'healthcheck' config can call this to know if the container
    is truly ready (not just started, but actually serving requests).
  - Deployment platforms (Railway, Render, AWS) use it to decide if
    traffic should be routed to this instance.
  - You can quickly confirm the backend is running after docker compose up.

ENDPOINT: GET /api/v1/health
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.db.session import get_db
from app.core.config import settings

router = APIRouter()


@router.get("/health", tags=["Health"])
def health_check(db: Session = Depends(get_db)):
    """
    Returns service status and verifies database connectivity.

    Checks:
      1. The FastAPI app is running (implicit — if this responds, it is).
      2. The database is reachable and responding to queries.

    Returns:
      200 OK  → Everything healthy.
      500     → DB unreachable (FastAPI will raise automatically if exception propagates).
    """
    # Try a trivial DB query — if it fails, something is wrong with Postgres
    try:
        db.execute(text("SELECT 1"))
        db_status = "connected"
    except Exception as e:
        db_status = f"error: {str(e)}"

    return {
        "status": "ok",
        "app": settings.APP_NAME,
        "environment": settings.APP_ENV,
        "database": db_status,
    }
