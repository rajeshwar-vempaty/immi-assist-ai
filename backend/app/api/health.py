"""Health check endpoints."""

from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.base import get_db
from app.services.rag_service import get_rag_service

router = APIRouter()

# Sample ingest seeds ~12 policy docs. Treat anything at/under this as sample mode
# unless a scraped raw corpus is present.
_SAMPLE_POLICY_CEILING = 20


def _knowledge_base_mode(policy_count: int) -> str:
    settings = get_settings()
    raw_candidates = [
        Path(settings.resolved_chroma_dir).resolve().parent / "raw" / "uscis_all_documents.json",
        Path(__file__).resolve().parents[2] / "data" / "raw" / "uscis_all_documents.json",
        Path("/workspace/backend/data/raw/uscis_all_documents.json"),
    ]
    scraped = any(p.exists() and p.stat().st_size > 1000 for p in raw_candidates)
    if scraped and policy_count > _SAMPLE_POLICY_CEILING:
        return "scraped"
    if policy_count <= _SAMPLE_POLICY_CEILING:
        return "sample"
    return "expanded"


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
    kb_mode = _knowledge_base_mode(policy_count)

    kb_ok = policy_count >= min_docs and timeline_count > 0
    require_scraped = settings.require_scraped_kb or (
        settings.app_env.lower() in ("production", "prod")
    )
    scraped_ok = (not require_scraped) or kb_mode != "sample"
    ready = db_ok and kb_ok and scraped_ok
    payload = {
        "status": "ready" if ready else "not_ready",
        "database": "ok" if db_ok else "error",
        "knowledge_base_documents": policy_count,
        "processing_times_documents": timeline_count,
        "min_required_documents": min_docs,
        "knowledge_base_mode": kb_mode,
        "require_scraped_kb": require_scraped,
        "scraped_kb_ok": scraped_ok,
        "chroma_persist_dir": settings.resolved_chroma_dir,
        "timestamp": datetime.utcnow().isoformat(),
    }
    if not ready:
        return JSONResponse(status_code=503, content=payload)
    return payload


@router.get("/health")
async def health_check():
    """Legacy health endpoint."""
    rag = get_rag_service()
    policy_count = rag.policy_collection.count()
    return {
        "status": "healthy",
        "knowledge_base_documents": policy_count,
        "knowledge_base_mode": _knowledge_base_mode(policy_count),
        "timestamp": datetime.utcnow().isoformat(),
    }
