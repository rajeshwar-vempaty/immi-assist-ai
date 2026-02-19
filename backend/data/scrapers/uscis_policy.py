"""
USCIS Data Scraper — Scrapes official USCIS sources for the knowledge base.

Sources:
1. USCIS Policy Manual (https://www.uscis.gov/policy-manual)
2. Form Instructions
3. Processing Times
4. News & Alerts

Run: python -m data.scrapers.uscis_policy
"""

import logging
import hashlib
import json
import time
from pathlib import Path
from dataclasses import dataclass, asdict

import httpx
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

# Base URLs
USCIS_BASE = "https://www.uscis.gov"
POLICY_MANUAL_URL = f"{USCIS_BASE}/policy-manual"
PROCESSING_TIMES_URL = f"{USCIS_BASE}/processing-times"

# Output directory for raw scraped data
RAW_DATA_DIR = Path(__file__).parent.parent.parent / "data" / "raw"


@dataclass
class ScrapedDocument:
    """A single scraped document chunk."""
    id: str
    title: str
    content: str
    source: str
    section: str
    url: str
    doc_type: str  # policy, form_instruction, processing_time, alert
    volume: str = ""
    part: str = ""
    chapter: str = ""


class USCISPolicyScraper:
    """Scrapes the USCIS Policy Manual and related documents."""

    def __init__(self):
        self.client = httpx.Client(
            timeout=30.0,
            headers={
                "User-Agent": "ImmiAssist-Research-Bot/1.0 (Educational/Informational)",
            },
            follow_redirects=True,
        )
        RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)

    def _make_id(self, text: str) -> str:
        """Generate a deterministic ID from content."""
        return hashlib.sha256(text.encode()).hexdigest()[:16]

    def _clean_text(self, soup_element) -> str:
        """Extract and clean text from a BeautifulSoup element."""
        if soup_element is None:
            return ""
        text = soup_element.get_text(separator="\n", strip=True)
        # Collapse multiple newlines
        while "\n\n\n" in text:
            text = text.replace("\n\n\n", "\n\n")
        return text.strip()

    def _chunk_text(self, text: str, max_chars: int = 1500, overlap: int = 200) -> list[str]:
        """Split text into overlapping chunks for embedding."""
        if len(text) <= max_chars:
            return [text]

        chunks = []
        start = 0
        while start < len(text):
            end = start + max_chars

            # Try to break at paragraph boundary
            if end < len(text):
                para_break = text.rfind("\n\n", start, end)
                if para_break > start + max_chars // 2:
                    end = para_break

            chunks.append(text[start:end].strip())
            start = end - overlap

        return [c for c in chunks if len(c) > 50]  # Skip tiny chunks

    # ----- Policy Manual Scraping -----

    def scrape_policy_manual_index(self) -> list[dict]:
        """Get the table of contents of the Policy Manual."""
        logger.info("Scraping Policy Manual index...")
        try:
            resp = self.client.get(POLICY_MANUAL_URL)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "lxml")

            volumes = []
            # Look for volume links in the policy manual page
            for link in soup.select("a[href*='/policy-manual/volume-']"):
                href = link.get("href", "")
                title = link.get_text(strip=True)
                if href and title:
                    full_url = href if href.startswith("http") else USCIS_BASE + href
                    volumes.append({"title": title, "url": full_url})

            logger.info(f"Found {len(volumes)} volumes in Policy Manual")
            return volumes

        except Exception as e:
            logger.error(f"Failed to scrape policy manual index: {e}")
            return []

    def scrape_page(self, url: str, doc_type: str = "policy") -> list[ScrapedDocument]:
        """Scrape a single USCIS page and chunk it."""
        try:
            resp = self.client.get(url)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "lxml")

            # Extract main content
            content_div = (
                soup.select_one("div.field--name-body")
                or soup.select_one("article")
                or soup.select_one("main")
            )
            if not content_div:
                logger.warning(f"No content found at {url}")
                return []

            title = soup.select_one("h1")
            title_text = title.get_text(strip=True) if title else "Untitled"

            full_text = self._clean_text(content_div)
            if len(full_text) < 50:
                return []

            # Chunk the content
            chunks = self._chunk_text(full_text)
            documents = []

            for i, chunk in enumerate(chunks):
                doc = ScrapedDocument(
                    id=self._make_id(f"{url}_{i}"),
                    title=title_text,
                    content=chunk,
                    source="USCIS Policy Manual",
                    section=title_text,
                    url=url,
                    doc_type=doc_type,
                )
                documents.append(doc)

            logger.info(f"Scraped {len(documents)} chunks from: {title_text}")
            return documents

        except Exception as e:
            logger.error(f"Failed to scrape {url}: {e}")
            return []

    # ----- Form Instructions -----

    def scrape_form_instructions(self, form_numbers: list[str] = None) -> list[ScrapedDocument]:
        """Scrape USCIS form instruction pages."""
        if form_numbers is None:
            form_numbers = [
                "i-129", "i-130", "i-140", "i-485", "i-765",
                "i-131", "i-20", "i-539", "i-864", "i-693",
                "i-526", "i-829", "i-751", "i-90", "n-400",
            ]

        all_docs = []
        for form in form_numbers:
            url = f"{USCIS_BASE}/{form}"
            logger.info(f"Scraping form: {form}")
            docs = self.scrape_page(url, doc_type="form_instruction")
            all_docs.extend(docs)
            time.sleep(1)  # Be respectful

        return all_docs

    # ----- Save Raw Data -----

    def save_documents(self, documents: list[ScrapedDocument], filename: str):
        """Save scraped documents to JSON for later ingestion."""
        output_path = RAW_DATA_DIR / f"{filename}.json"
        data = [asdict(doc) for doc in documents]
        output_path.write_text(json.dumps(data, indent=2))
        logger.info(f"Saved {len(documents)} documents to {output_path}")

    # ----- Full Scrape Pipeline -----

    def run_full_scrape(self):
        """Run the complete scraping pipeline."""
        logger.info("=" * 60)
        logger.info("Starting USCIS data scrape")
        logger.info("=" * 60)

        all_documents = []

        # 1. Policy Manual
        volumes = self.scrape_policy_manual_index()
        for vol in volumes[:5]:  # Start with first 5 volumes for MVP
            docs = self.scrape_page(vol["url"])
            all_documents.extend(docs)
            time.sleep(1)

        # 2. Form Instructions
        form_docs = self.scrape_form_instructions()
        all_documents.extend(form_docs)

        # Save everything
        self.save_documents(all_documents, "uscis_all_documents")

        logger.info(f"Scraping complete! Total documents: {len(all_documents)}")
        return all_documents


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    scraper = USCISPolicyScraper()
    scraper.run_full_scrape()
