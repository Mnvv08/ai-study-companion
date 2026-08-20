"""
app/db/session.py
─────────────────
SQLAlchemy engine + session factory setup.

KEY CONCEPTS:
  engine       → The actual connection to PostgreSQL (one per app).
  SessionLocal → A factory that creates per-request DB sessions.
                 We use it as a FastAPI dependency (see below).
  get_db()     → A generator function used as a FastAPI dependency.
                 It yields a session, and closes it after the request —
                 even if the request raises an exception (via finally).
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from typing import Generator

from app.core.config import settings


# ── Engine ────────────────────────────────────────────────────────
# pool_pre_ping=True: Before using a connection from the pool,
# test it. Prevents "server closed connection" errors after idle time.
engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    echo=settings.DEBUG,   # Log SQL queries in development — helpful for learning!
)

# ── Session factory ───────────────────────────────────────────────
# autocommit=False: You must call session.commit() explicitly.
# autoflush=False:  Changes aren't flushed to DB until you commit.
# This gives you control — no surprise writes to the database.
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)


# ── FastAPI DB Dependency ─────────────────────────────────────────
def get_db() -> Generator[Session, None, None]:
    """
    FastAPI dependency that provides a database session per request.

    Usage in a route:
        @router.get("/example")
        def example(db: Session = Depends(get_db)):
            ...

    The 'yield' makes this a generator — FastAPI calls everything
    before yield for setup, and everything after yield for cleanup,
    EVEN if the route handler raises an exception.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()  # Always close, even on error
