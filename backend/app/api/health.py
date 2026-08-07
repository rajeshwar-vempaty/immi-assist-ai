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

# Sample ingest seeds ~12 policy docs. Counts at/under this are treated as sample
# unless a scraped raw corpus (or corpus_manifest) is present.
_SAMPLE_POLICY_CEILING = 20


def _raw_corpus_paths() -> list[Path]:
    settings = get_settings()
    chroma_parent = Path(settings.resolved_chroma_dir).resolve().parent
    backend_data = Path(__file__).resolve().parents[2] / "data"
    return [
        chroma_parent / "raw" / "uscis_all_documents.json",
        chroma_parent / "raw" / "corpus_manifest.json",
        backend_data / "raw" / "uscis_all_documents.json",
        backend_data / "raw" / "corpus_manifest.json",
        Path("/workspace/backend/data/raw/uscis_all_documents.json"),
        Path("/workspace/backend/data/raw/corpus_manifest.json"),
    ]


def _has_scraped_raw_corpus() -> bool:
    """True when a non-trivial scraped corpus (or manifest) exists on disk."""
    for path in _raw_corpus_paths():
        if not path.exists():
            continue
        try:
            size = path.stat().st_size
        except OSError:
            continue
        if path.name == "corpus_manifest.json" and size > 40:
            try:
                import json

                payload = json.loads(path.read_text(encoding="utf-8"))
                if payload.get("corpus_origin") == "scraped" and int(
                    payload.get("document_count") or 0
                ) > 0:
                    return True
            except Exception:
                continue
        if path.name == "uscis_all_documents.json" and size > 1000:
            return True
    return False


def _knowledge_base_mode(policy_count: int) -> str:
    scraped_on_disk = _has_scraped_raw_corpus()
    if scraped_on_disk and policy_count > 0:
        # Scraped corpus present — even capped chapter runs (<20 docs) count as scraped.
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
    # Only enforce when explicitly configured. Do NOT imply from APP_ENV=production —
    # prod compose starts with sample ingest and the scheduler depends on /health/ready.
    require_scraped = bool(settings.require_scraped_kb)
    scraped_ok = (not require_scraped) or kb_mode == "scraped"
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
