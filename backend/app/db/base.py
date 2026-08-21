"""
app/db/base.py
──────────────
Declarative base for all SQLAlchemy models.

IMPORTANT: Do NOT import models here — that causes circular imports.
Models import Base from this file; main.py imports the models to trigger
SQLAlchemy metadata discovery before create_all() runs.
"""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass
