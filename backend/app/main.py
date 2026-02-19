"""
ImmiAssist AI — FastAPI Application Entry Point
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.api import chat

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(name)s | %(levelname)s | %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    settings = get_settings()
    logger.info(f"Starting {settings.app_name} in {settings.app_env} mode")
    logger.info(f"Reasoning model: {settings.reasoning_model}")
    logger.info(f"Classifier model: {settings.classifier_model}")

    # Validate API keys are present
    missing_keys = []
    if not settings.openai_api_key:
        missing_keys.append("OPENAI_API_KEY")
    if not settings.anthropic_api_key:
        missing_keys.append("ANTHROPIC_API_KEY")
    if not settings.google_api_key:
        missing_keys.append("GOOGLE_API_KEY")

    if missing_keys:
        logger.warning(f"⚠️ Missing API keys: {', '.join(missing_keys)}")
        logger.warning("Some features may not work without all API keys configured.")
    else:
        logger.info("✅ All API keys configured")

    yield  # Application runs here

    logger.info("Shutting down ImmiAssist AI")


# Create FastAPI app
app = FastAPI(
    title="ImmiAssist AI",
    description=(
        "AI-powered immigration guidance platform using multi-LLM orchestration "
        "and RAG over official USCIS sources."
    ),
    version="0.1.0",
    lifespan=lifespan,
)

# CORS
settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routes
app.include_router(chat.router, prefix="/api/v1", tags=["Chat"])


@app.get("/")
async def root():
    return {
        "name": "ImmiAssist AI",
        "version": "0.1.0",
        "status": "running",
        "docs": "/docs",
    }
