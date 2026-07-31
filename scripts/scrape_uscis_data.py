#!/usr/bin/env python3
"""
Scrape USCIS Policy Manual (+ optional Visa Bulletin) into backend/data/raw/.

Usage:
  python scripts/scrape_uscis_data.py
  python scripts/scrape_uscis_data.py --deep --max-chapters 40
  python scripts/scrape_uscis_data.py --all-volumes --max-chapters 80
  python scripts/scrape_uscis_data.py --visa-bulletin
  python scripts/scrape_uscis_data.py --deep --visa-bulletin --forms
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))

from data.scrapers.uscis_policy import USCISPolicyScraper  # noqa: E402
from data.scrapers.visa_bulletin import VisaBulletinScraper  # noqa: E402


def _doc_to_dict(doc: Any) -> Dict[str, Any]:
    if hasattr(doc, "__dataclass_fields__"):
        return asdict(doc)
    if isinstance(doc, dict):
        return doc
    return dict(doc)


def _merge_documents(*doc_lists: List[Any]) -> List[Dict[str, Any]]:
    seen = set()
    merged: List[Dict[str, Any]] = []
    for docs in doc_lists:
        for raw in docs:
            doc = _doc_to_dict(raw)
            key = (doc.get("url") or "").rstrip("/") or doc.get("id") or doc.get("title")
            content_key = (key, (doc.get("content") or "")[:80])
            if content_key in seen:
                continue
            seen.add(content_key)
            merged.append(doc)
    return merged


def _write_manifest(raw_dir: Path, all_docs: List[Dict[str, Any]], includes_visa: bool) -> None:
    by_type: Dict[str, int] = {}
    for d in all_docs:
        dt = d.get("doc_type") or "policy"
        by_type[dt] = by_type.get(dt, 0) + 1
    manifest = {
        "corpus_origin": "scraped" if all_docs else "empty",
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "document_count": len(all_docs),
        "by_doc_type": by_type,
        "unique_urls": len({(d.get("url") or "") for d in all_docs if d.get("url")}),
        "includes_visa_bulletin": includes_visa,
    }
    (raw_dir / "corpus_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Scrape USCIS / Visa Bulletin into backend/data/raw")
    parser.add_argument(
        "--deep",
        action="store_true",
        help="Discover chapter URLs from each volume index (recommended)",
    )
    parser.add_argument(
        "--all-volumes",
        action="store_true",
        help="Scrape Policy Manual volumes 1–16 (still subject to --max-chapters)",
    )
    parser.add_argument(
        "--volumes",
        type=str,
        default=None,
        help="Comma-separated volume numbers (default: 6,7,8,9,12)",
    )
    parser.add_argument(
        "--max-chapters",
        type=int,
        default=None,
        help="Cap total chapter pages scraped (safety valve for CI / first runs)",
    )
    parser.add_argument(
        "--forms",
        action="store_true",
        help="Also scrape common form instruction pages",
    )
    parser.add_argument(
        "--visa-bulletin",
        action="store_true",
        help="Also scrape latest Visa Bulletin into structured JSON + RAG paragraphs",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=1.0,
        help="Seconds between HTTP requests (default 1.0)",
    )
    args = parser.parse_args()

    volume_numbers: Optional[List[int]]
    if args.all_volumes:
        volume_numbers = list(range(1, 17))
    elif args.volumes:
        volume_numbers = [int(v.strip()) for v in args.volumes.split(",") if v.strip()]
    else:
        volume_numbers = [6, 7, 8, 9, 12]

    raw_dir = BACKEND / "data" / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)

    scraper = USCISPolicyScraper(delay_seconds=args.delay)
    print("=" * 60)
    print("Beacon — USCIS Policy Manual scrape")
    print("=" * 60)
    print(
        f"  deep={args.deep or args.all_volumes}  volumes={volume_numbers}  "
        f"max_chapters={args.max_chapters}"
    )

    policy_docs = scraper.scrape_policy_manual(
        volume_numbers=volume_numbers,
        max_chapters=args.max_chapters,
        deep=args.deep or args.all_volumes,
    )
    print(f"Policy documents scraped: {len(policy_docs)}")

    form_docs: List[Any] = []
    if args.forms:
        form_docs = scraper.scrape_form_instructions()
        print(f"Form pages scraped: {len(form_docs)}")

    visa_docs: List[Dict[str, Any]] = []
    if args.visa_bulletin:
        print("-" * 60)
        print("Visa Bulletin scrape")
        vb = VisaBulletinScraper(delay=args.delay)
        bulletin = vb.scrape_latest()
        structured = {k: v for k, v in bulletin.items() if k != "rag_documents"}
        structured["rag_document_count"] = len(bulletin.get("rag_documents") or [])
        visa_path = raw_dir / "visa_bulletin_latest.json"
        visa_path.write_text(json.dumps(structured, indent=2), encoding="utf-8")
        print(f"  Saved structured bulletin → {visa_path}")
        visa_docs = vb.to_rag_documents(bulletin)
        visa_rag_path = raw_dir / "visa_bulletin_rag.json"
        visa_rag_path.write_text(json.dumps(visa_docs, indent=2), encoding="utf-8")
        print(f"  Saved RAG paragraphs ({len(visa_docs)}) → {visa_rag_path}")

    all_docs = _merge_documents(policy_docs, form_docs, visa_docs)
    out_path = raw_dir / "uscis_all_documents.json"
    out_path.write_text(json.dumps(all_docs, indent=2), encoding="utf-8")
    _write_manifest(raw_dir, all_docs, includes_visa=bool(visa_docs))

    print("-" * 60)
    print(f"Merged corpus: {len(all_docs)} documents → {out_path}")
    print("Next: python scripts/ingest_uscis_data.py --yes")
    return 0 if all_docs else 1


if __name__ == "__main__":
    raise SystemExit(main())
