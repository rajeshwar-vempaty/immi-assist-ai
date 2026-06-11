"""Health check endpoints."""

from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.base import get_db
from app.services.rag_service import get_rag_service

router = APIRouter()


@router.get("/health/live")
async def liveness():
    return {"status": "alive", "timestamp": datetime.utcnow().isoformat()}


@router.get("/health/ready")
async def readiness(db: Session = Depends(get_db)):
    db_ok = False
    try:
        db.execute(text("SELECT 1"))
        db_ok = True
    except Exception:
        pass

    settings = get_settings()
    rag = get_rag_service()
    policy_count = rag.policy_collection.count()
    timeline_count = rag.timeline_collection.count()
    min_docs = settings.min_knowledge_base_documents

    kb_ok = policy_count >= min_docs and timeline_count > 0
    ready = db_ok and kb_ok

    return {
        "status": "ready" if ready else "not_ready",
        "database": "ok" if db_ok else "error",
        "knowledge_base_documents": policy_count,
        "processing_times_documents": timeline_count,
        "min_required_documents": min_docs,
        "timestamp": datetime.utcnow().isoformat(),
    }


@router.get("/health")
async def health_check():
    """Legacy health endpoint."""
    rag = get_rag_service()
    return {
        "status": "healthy",
        "knowledge_base_documents": rag.policy_collection.count(),
        "timestamp": datetime.utcnow().isoformat(),
    }
