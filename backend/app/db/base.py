"""
app/db/base.py
──────────────
Declarative base for all SQLAlchemy models.

WHY a separate base.py?
  All your models (User, UploadedFile, QuizResult, etc.) must inherit
  from the same Base class so SQLAlchemy knows they belong to the same
  metadata registry. Alembic also needs to import this Base to detect
  model changes and auto-generate migrations.

  In Phase 1, you'll also import all models here so Alembic can see them:
    from app.models.user import User        # noqa: F401
    from app.models.file import UploadedFile  # noqa: F401
"""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """
    Base class for all database models.
    All models do: class User(Base): ...
    """
    pass
