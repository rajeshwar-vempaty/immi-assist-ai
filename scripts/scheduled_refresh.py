#!/usr/bin/env python3
"""
Scheduled USCIS knowledge base refresh.

Runs scrape + ingest on a configurable interval (default: weekly).

Usage:
    python scripts/scheduled_refresh.py
    INGEST_INTERVAL_HOURS=24 python scripts/scheduled_refresh.py
"""

import logging
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
SCRAPE_SCRIPT = REPO_ROOT / "scripts" / "scrape_uscis_data.py"
INGEST_SCRIPT = REPO_ROOT / "scripts" / "ingest_uscis_data.py"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)
logger = logging.getLogger(__name__)


def run_refresh() -> bool:
    """Execute scrape then ingest pipeline."""
    logger.info("=" * 60)
    logger.info("Scheduled knowledge base refresh starting")
    logger.info("=" * 60)

    scrape = subprocess.run(
        [sys.executable, str(SCRAPE_SCRIPT)],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
    )
    if scrape.returncode != 0:
        logger.error(f"Scrape failed: {scrape.stderr[-1000:]}")
        return False
    logger.info(scrape.stdout[-500:] if scrape.stdout else "Scrape completed")

    ingest = subprocess.run(
        [sys.executable, str(INGEST_SCRIPT), "--yes"],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
    )
    if ingest.returncode != 0:
        logger.error(f"Ingest failed: {ingest.stderr[-1000:]}")
        return False
    logger.info(ingest.stdout[-500:] if ingest.stdout else "Ingest completed")

    logger.info(f"Refresh completed at {datetime.utcnow().isoformat()}Z")
    return True


def main():
    interval_hours = int(os.getenv("INGEST_INTERVAL_HOURS", "168"))
    run_on_start = os.getenv("RUN_REFRESH_ON_START", "true").lower() == "true"
    interval_seconds = interval_hours * 3600

    logger.info(f"Scheduler started. Interval: every {interval_hours} hours")

    if run_on_start:
        run_refresh()

    while True:
        logger.info(f"Next refresh in {interval_hours} hours")
        time.sleep(interval_seconds)
        run_refresh()


if __name__ == "__main__":
    main()
