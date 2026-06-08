"""Admin endpoints."""

import subprocess
import sys
from pathlib import Path

from fastapi import APIRouter, Depends, Header, HTTPException

from app.core.config import get_settings

router = APIRouter(prefix="/admin", tags=["Admin"])


def verify_admin(x_admin_key: str = Header(..., alias="X-Admin-Key")):
    settings = get_settings()
    if not settings.admin_api_key or x_admin_key != settings.admin_api_key:
        raise HTTPException(status_code=403, detail="Invalid admin key")


@router.post("/scrape", dependencies=[Depends(verify_admin)])
async def trigger_scrape():
    """Run USCIS scrape pipeline (requires ADMIN_API_KEY)."""
    scrape_script = Path(__file__).resolve().parents[3] / "scripts" / "scrape_uscis_data.py"
    result = subprocess.run(
        [sys.executable, str(scrape_script)],
        capture_output=True,
        text=True,
        cwd=str(scrape_script.parent.parent),
        timeout=600,
    )
    if result.returncode != 0:
        raise HTTPException(status_code=500, detail=result.stderr or "Scrape failed")
    return {"status": "completed", "output": result.stdout[-2000:]}


@router.post("/ingest", dependencies=[Depends(verify_admin)])
async def trigger_ingest(scrape: bool = False):
    """Trigger knowledge base ingestion (requires ADMIN_API_KEY)."""
    ingest_script = Path(__file__).resolve().parents[3] / "scripts" / "ingest_uscis_data.py"
    cmd = [sys.executable, str(ingest_script), "--yes"]
    if scrape:
        cmd.append("--scrape")

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        cwd=str(ingest_script.parent.parent),
        timeout=900,
    )
    if result.returncode != 0:
        raise HTTPException(status_code=500, detail=result.stderr or "Ingestion failed")
    return {"status": "completed", "output": result.stdout[-2000:]}
