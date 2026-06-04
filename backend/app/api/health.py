"""Health check endpoints."""

from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

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

    rag = get_rag_service()
    doc_count = rag.policy_collection.count()

    ready = db_ok and doc_count > 0
    return {
        "status": "ready" if ready else "not_ready",
        "database": "ok" if db_ok else "error",
        "knowledge_base_documents": doc_count,
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
