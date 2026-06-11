"""
USCIS scrape pipeline — policy manual + forms.

Usage (from repo root):
    python scripts/scrape_uscis_data.py
    python scripts/scrape_uscis_data.py --forms-only
    python scripts/scrape_uscis_data.py --policy-only
"""

import argparse
import json
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger(__name__)

RAW_DIR = Path(__file__).parent.parent / "backend" / "data" / "raw"


def scrape_policy(max_volumes: int = 5) -> list[dict]:
    from data.scrapers.uscis_policy import USCISPolicyScraper

    scraper = USCISPolicyScraper()
    all_docs = []

    volumes = scraper.scrape_policy_manual_index()
    for vol in volumes[:max_volumes]:
        docs = scraper.scrape_page(vol["url"])
        all_docs.extend(
            {
                "content": d.content,
                "source": d.source,
                "section": d.section or d.title,
                "doc_type": d.doc_type,
                "url": d.url,
            }
            for d in docs
        )

    output = RAW_DIR / "uscis_policy.json"
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(all_docs, indent=2))
    logger.info(f"Saved {len(all_docs)} policy chunks to {output}")
    return all_docs


def scrape_forms() -> list[dict]:
    from data.scrapers.uscis_forms import save_forms

    output = save_forms()
    return json.loads(output.read_text())


def merge_corpus() -> Path:
    """Merge policy + forms into uscis_all_documents.json for ingest."""
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    merged = []

    for filename in ("uscis_policy.json", "uscis_forms.json"):
        path = RAW_DIR / filename
        if path.exists():
            merged.extend(json.loads(path.read_text()))

    output = RAW_DIR / "uscis_all_documents.json"
    output.write_text(json.dumps(merged, indent=2))
    logger.info(f"Merged corpus: {len(merged)} documents -> {output}")
    return output


def main():
    parser = argparse.ArgumentParser(description="Scrape USCIS data")
    parser.add_argument("--policy-only", action="store_true")
    parser.add_argument("--forms-only", action="store_true")
    parser.add_argument("--max-volumes", type=int, default=5)
    args = parser.parse_args()

    if args.forms_only:
        scrape_forms()
    elif args.policy_only:
        scrape_policy(max_volumes=args.max_volumes)
    else:
        scrape_policy(max_volumes=args.max_volumes)
        scrape_forms()

    merge_corpus()


if __name__ == "__main__":
    main()
