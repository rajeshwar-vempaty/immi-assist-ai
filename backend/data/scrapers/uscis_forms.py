"""
USCIS form instructions scraper.

Scrapes official form pages and saves JSON for the ingestion pipeline.
Run from backend directory:
    python -m data.scrapers.uscis_forms
"""

import logging
import sys
from pathlib import Path

# Allow running as module from backend/
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from data.scrapers.uscis_policy import USCISPolicyScraper, RAW_DATA_DIR

logger = logging.getLogger(__name__)

DEFAULT_FORMS = [
    "i-129", "i-130", "i-140", "i-485", "i-765",
    "i-131", "i-539", "i-864", "i-693", "i-526",
    "i-829", "i-751", "i-90", "n-400", "i-821",
]


def scrape_forms(form_numbers: list[str] | None = None) -> list[dict]:
    """Scrape form instruction pages and return ingest-ready documents."""
    scraper = USCISPolicyScraper()
    docs = scraper.scrape_form_instructions(form_numbers or DEFAULT_FORMS)
    return [
        {
            "content": doc.content,
            "source": doc.source,
            "section": doc.section or doc.title,
            "doc_type": doc.doc_type,
            "url": doc.url,
        }
        for doc in docs
    ]


def save_forms(form_numbers: list[str] | None = None) -> Path:
    """Scrape and save forms to backend/data/raw/uscis_forms.json."""
    scraper = USCISPolicyScraper()
    docs = scraper.scrape_form_instructions(form_numbers or DEFAULT_FORMS)
    RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)
    output = RAW_DATA_DIR / "uscis_forms.json"
    data = [
        {
            "content": doc.content,
            "source": doc.source,
            "section": doc.section or doc.title,
            "doc_type": doc.doc_type,
            "url": doc.url,
        }
        for doc in docs
    ]
    import json

    output.write_text(json.dumps(data, indent=2))
    logger.info(f"Saved {len(data)} form chunks to {output}")
    return output


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    save_forms()
