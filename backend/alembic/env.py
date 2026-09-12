"""
alembic/env.py
──────────────
Wires Alembic to the application's own configuration and metadata.

Two deliberate choices here:

1. The database URL comes from `settings.DATABASE_URL`, not from
   alembic.ini. One source of truth, and no credentials in git.

2. Every model module is imported below so that `Base.metadata` is fully
   populated before autogenerate inspects it. A model that isn't imported
   is invisible to Alembic, and autogenerate will cheerfully emit a
   migration that drops its table.
"""

from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from app.core.config import settings
from app.db.base import Base

# Importing for the metadata side effect only — do not remove.
from app.models import user, file, quiz, review  # noqa: F401

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Emit SQL to stdout without connecting to a database."""
    context.configure(
        url=settings.DATABASE_URL,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Connect to the database and run migrations against it."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            # Without this, a column changing from String(50) to String(100)
            # is silently ignored by autogenerate.
            compare_type=True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
