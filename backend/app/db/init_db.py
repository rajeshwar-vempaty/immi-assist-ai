"""
Initialize database tables on application startup.
"""

import logging

from app.db.base import Base, engine

logger = logging.getLogger(__name__)

# Import models so they register with Base.metadata
from app.models import models  # noqa: F401


def init_db() -> None:
    """Create all tables if they do not exist."""
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables initialized")
