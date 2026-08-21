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

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
import logging

from app.db.session import get_db
from app.core.config import settings

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/health", tags=["Health"])
def health_check(db: Session = Depends(get_db)):
    """
    Returns service status and verifies database connectivity.

    Checks:
      1. The FastAPI app is running.
      2. The database is reachable and responding.

    Returns:
      200 OK  → Everything healthy.
      500     → DB unreachable.
    """
    try:
        db.execute(text("SELECT 1"))
    except Exception as e:
        logger.error(f"Health check failed - Database connectivity error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Database connection error: {str(e)}"
        )

    return {
        "status": "healthy",
        "app": settings.APP_NAME,
        "environment": settings.APP_ENV,
        "database": "connected",
    }

