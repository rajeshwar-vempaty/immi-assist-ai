"""
Initialize database tables on application startup.
"""

import logging

from sqlalchemy import inspect, text

from app.db.base import Base, engine

logger = logging.getLogger(__name__)

from app.models import models  # noqa: F401


def _add_column_if_missing(table: str, column: str, ddl: str) -> None:
    inspector = inspect(engine)
    if table not in inspector.get_table_names():
        return
    existing = {c["name"] for c in inspector.get_columns(table)}
    if column in existing:
        return
    with engine.begin() as conn:
        conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {ddl}"))
    logger.info(f"Added column {table}.{column}")


def init_db() -> None:
    """Create all tables if they do not exist and apply lightweight SQLite alters."""
    Base.metadata.create_all(bind=engine)
    _add_column_if_missing("users", "name", "name VARCHAR(255)")
    _add_column_if_missing("users", "picture", "picture TEXT")
    _add_column_if_missing("users", "google_sub", "google_sub VARCHAR(255)")
    _add_column_if_missing("users", "password_hash", "password_hash VARCHAR(255)")
    _add_column_if_missing("users", "updated_at", "updated_at DATETIME")
    logger.info("Database tables initialized")
