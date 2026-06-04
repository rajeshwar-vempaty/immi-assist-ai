"""
ImmiAssist AI — FastAPI Application Entry Point
"""

import logging
import sys

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import admin, auth, chat, checklist, health, rfe, timeline
from app.core.config import get_settings
from app.core.exceptions import register_exception_handlers
from app.db.init_db import init_db
from app.middleware.request_id import RequestIDMiddleware

settings = get_settings()

log_level = logging.DEBUG if settings.debug else logging.INFO
log_format = (
    "%(asctime)s | %(name)s | %(levelname)s | %(message)s"
    if settings.app_env != "production"
    else '{"time":"%(asctime)s","name":"%(name)s","level":"%(levelname)s","message":"%(message)s"}'
)
logging.basicConfig(level=log_level, format=log_format, stream=sys.stdout)
logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    from contextlib import asynccontextmanager

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        logger.info(f"Starting {settings.app_name} in {settings.app_env} mode")
        init_db()

        missing_keys = []
        if not settings.openai_api_key:
            missing_keys.append("OPENAI_API_KEY")
        if not settings.anthropic_api_key:
            missing_keys.append("ANTHROPIC_API_KEY")
        if not settings.google_api_key:
            missing_keys.append("GOOGLE_API_KEY")

        if missing_keys:
            logger.warning(f"Missing API keys: {', '.join(missing_keys)}")
        else:
            logger.info("All API keys configured")

        yield
        logger.info("Shutting down ImmiAssist AI")

    app = FastAPI(
        title="ImmiAssist AI",
        description=(
            "AI-powered immigration guidance platform using multi-LLM orchestration "
            "and RAG over official USCIS sources."
        ),
        version="1.0.0",
        lifespan=lifespan,
    )

    app.add_middleware(RequestIDMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["*"],
    )

    register_exception_handlers(app)

    app.include_router(health.router, prefix="/api/v1", tags=["Health"])
    app.include_router(chat.router, prefix="/api/v1", tags=["Chat"])
    app.include_router(checklist.router, prefix="/api/v1", tags=["Checklist"])
    app.include_router(timeline.router, prefix="/api/v1", tags=["Timeline"])
    app.include_router(rfe.router, prefix="/api/v1", tags=["RFE"])
    app.include_router(auth.router, prefix="/api/v1")
    app.include_router(admin.router, prefix="/api/v1")

    @app.get("/")
    async def root():
        return {
            "name": settings.app_name,
            "version": "1.0.0",
            "status": "running",
            "docs": "/docs",
        }

    return app


app = create_app()
