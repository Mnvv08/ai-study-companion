"""
app/db/base.py
──────────────
Declarative base for all SQLAlchemy models.
Import all models here so SQLAlchemy and Alembic discover them.
"""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


# Register all models here for metadata discovery
from app.models.user import User  # noqa: F401, E402
from app.models.file import UploadedFile  # noqa: F401, E402
