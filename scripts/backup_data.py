#!/usr/bin/env python3
"""
Backup SQLite database and ChromaDB vector store.

Usage (from repo root):
    python scripts/backup_data.py
    python scripts/backup_data.py --output ./backups
"""

import argparse
import logging
import shutil
from datetime import datetime
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).parent.parent
DEFAULT_DB = REPO_ROOT / "backend" / "immi_assist.db"
DEFAULT_CHROMA = REPO_ROOT / "backend" / "data" / "chroma_db"


def backup(output_dir: Path, db_path: Path, chroma_path: Path) -> Path:
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    dest = output_dir / f"immi_assist_backup_{timestamp}"
    dest.mkdir(parents=True, exist_ok=True)

    if db_path.exists():
        shutil.copy2(db_path, dest / db_path.name)
        logger.info(f"Backed up database: {db_path}")
    else:
        logger.warning(f"Database not found: {db_path}")

    if chroma_path.exists():
        shutil.copytree(chroma_path, dest / "chroma_db")
        logger.info(f"Backed up ChromaDB: {chroma_path}")
    else:
        logger.warning(f"ChromaDB not found: {chroma_path}")

    logger.info(f"Backup complete: {dest}")
    return dest


def main():
    parser = argparse.ArgumentParser(description="Backup ImmiAssist data")
    parser.add_argument("--output", default=str(REPO_ROOT / "backups"))
    parser.add_argument("--db", default=str(DEFAULT_DB))
    parser.add_argument("--chroma", default=str(DEFAULT_CHROMA))
    args = parser.parse_args()

    backup(Path(args.output), Path(args.db), Path(args.chroma))


if __name__ == "__main__":
    main()
