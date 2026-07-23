"""
Beacon — FastAPI Application Entry Point
"""

import logging
import sys

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.api import admin, auth, chat, checklist, conversations, health, rfe, timeline
from app.api import settings as settings_api
from app.core.config import get_settings
from app.core.exceptions import register_exception_handlers
from app.core.logging_filters import install_redacting_filter
from app.core.validation import validate_production_settings
from app.db.init_db import init_db
from app.middleware.request_id import RequestIDMiddleware
from app.observability.metrics import PrometheusMiddleware, metrics_endpoint
from app.observability.sentry import init_sentry

settings = get_settings()

log_level = logging.DEBUG if settings.debug else logging.INFO
log_format = (
    "%(asctime)s | %(name)s | %(levelname)s | %(message)s"
    if settings.app_env != "production"
    else '{"time":"%(asctime)s","name":"%(name)s","level":"%(levelname)s","message":"%(message)s"}'
)
logging.basicConfig(level=log_level, format=log_format, stream=sys.stdout)
install_redacting_filter()
logger = logging.getLogger(__name__)


def _docs_enabled() -> bool:
    if settings.expose_api_docs is not None:
        return settings.expose_api_docs
    return settings.app_env != "production"


def create_app() -> FastAPI:
    from contextlib import asynccontextmanager

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        logger.info(f"Starting {settings.app_name} in {settings.app_env} mode")
        validate_production_settings(settings)
        init_sentry(settings)
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
        logger.info("Shutting down Beacon")

    docs_on = _docs_enabled()
    app = FastAPI(
        title="Beacon",
        description=(
            "AI-powered immigration guidance platform using multi-LLM orchestration "
            "and RAG over official USCIS sources."
        ),
        version="1.0.0",
        lifespan=lifespan,
        docs_url="/docs" if docs_on else None,
        redoc_url="/redoc" if docs_on else None,
        openapi_url="/openapi.json" if docs_on else None,
    )

    app.add_middleware(RequestIDMiddleware)
    if settings.metrics_enabled:
        app.add_middleware(PrometheusMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["*"],
    )

    register_exception_handlers(app)

    app.include_router(health.router, prefix="/api/v1", tags=["Health"])
    app.include_router(chat.router, prefix="/api/v1", tags=["Chat"])
    app.include_router(checklist.router, prefix="/api/v1", tags=["Checklist"])
    app.include_router(timeline.router, prefix="/api/v1", tags=["Timeline"])
    app.include_router(rfe.router, prefix="/api/v1", tags=["RFE"])
    app.include_router(auth.router, prefix="/api/v1")
    app.include_router(settings_api.router, prefix="/api/v1")
    app.include_router(conversations.router, prefix="/api/v1")
    app.include_router(admin.router, prefix="/api/v1")

    @app.get("/")
    async def root():
        payload = {
            "name": settings.app_name,
            "version": "1.0.0",
            "status": "running",
        }
        if docs_on:
            payload["docs"] = "/docs"
        return payload

    if settings.metrics_enabled:
        if settings.metrics_require_admin:

            async def _metrics(
                x_admin_key: str | None = Header(None, alias="X-Admin-Key"),
            ):
                if not settings.admin_api_key or x_admin_key != settings.admin_api_key:
                    raise HTTPException(status_code=403, detail="Metrics require admin key")
                return metrics_endpoint()

            app.add_api_route("/metrics", _metrics, methods=["GET"], include_in_schema=False)
        else:
            app.add_api_route("/metrics", metrics_endpoint, methods=["GET"], include_in_schema=False)

    return app


app = create_app()
