"""
USCIS Policy Manual scraper — volumes, chapters, and form pages.

Sources:
1. USCIS Policy Manual (https://www.uscis.gov/policy-manual)
2. Form instruction pages

Run: python -m data.scrapers.uscis_policy
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

USCIS_BASE = "https://www.uscis.gov"
POLICY_MANUAL_URL = f"{USCIS_BASE}/policy-manual"

RAW_DATA_DIR = Path(__file__).parent.parent / "raw"


@dataclass
class ScrapedDocument:
    """A single scraped document chunk."""

    id: str
    title: str
    content: str
    source: str
    section: str
    url: str
    doc_type: str  # policy, form_instruction, visa_bulletin, processing_time, alert
    volume: str = ""
    part: str = ""
    chapter: str = ""
    effective_date: str = ""
    scraped_at: str = ""
    corpus_origin: str = "scraped"


class USCISPolicyScraper:
    """Scrapes the USCIS Policy Manual and related documents."""

    def __init__(self, delay_seconds: float = 0.75):
        self.delay_seconds = delay_seconds
        self.client = httpx.Client(
            timeout=30.0,
            headers={
                "User-Agent": (
                    "Beacon-Research-Bot/2.0 (+https://github.com/rajeshwar-vempaty/immi-assist-ai; "
                    "informational immigration guidance)"
                ),
                "Accept": "text/html,application/xhtml+xml",
                "Accept-Language": "en-US,en;q=0.9",
            },
            follow_redirects=True,
        )
        RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)
        self._visited: set[str] = set()

    def _make_id(self, text: str) -> str:
        return hashlib.sha256(text.encode()).hexdigest()[:16]

    def _clean_text(self, soup_element) -> str:
        if soup_element is None:
            return ""
        text = soup_element.get_text(separator="\n", strip=True)
        while "\n\n\n" in text:
            text = text.replace("\n\n\n", "\n\n")
        return text.strip()

    def _chunk_text(self, text: str, max_chars: int = 1500, overlap: int = 200) -> list[str]:
        if len(text) <= max_chars:
            return [text]
        chunks = []
        start = 0
        while start < len(text):
            end = start + max_chars
            if end < len(text):
                para_break = text.rfind("\n\n", start, end)
                if para_break > start + max_chars // 2:
                    end = para_break
            chunks.append(text[start:end].strip())
            start = end - overlap
        return [c for c in chunks if len(c) > 50]

    def _normalize_url(self, href: str) -> str:
        if not href:
            return ""
        full = href if href.startswith("http") else urljoin(USCIS_BASE, href)
        parsed = urlparse(full)
        return f"{parsed.scheme}://{parsed.netloc}{parsed.path}".rstrip("/")

    def _extract_effective_date(self, soup: BeautifulSoup) -> str:
        text = soup.get_text(" ", strip=True)
        patterns = [
            r"Current as of\s+([A-Za-z]+\s+\d{1,2},\s+\d{4})",
            r"Effective\s+([A-Za-z]+\s+\d{1,2},\s+\d{4})",
            r"Last reviewed/updated:\s*([A-Za-z]+\s+\d{1,2},\s+\d{4})",
        ]
        for pat in patterns:
            m = re.search(pat, text, re.IGNORECASE)
            if m:
                return m.group(1)
        return ""

    def _volume_label(self, title: str, url: str) -> str:
        m = re.search(r"volume[- ]?(\d+)", f"{title} {url}", re.IGNORECASE)
        return f"Volume {m.group(1)}" if m else (title or "")

    def scrape_policy_manual_index(self) -> list[dict]:
        """Get the table of contents of the Policy Manual."""
        logger.info("Scraping Policy Manual index...")
        try:
            resp = self.client.get(POLICY_MANUAL_URL)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "lxml")
            volumes = []
            seen = set()
            for link in soup.select("a[href*='/policy-manual/volume-']"):
                href = self._normalize_url(link.get("href", ""))
                title = link.get_text(strip=True)
                if not href or href in seen:
                    continue
                seen.add(href)
                volumes.append({"title": title or href.split("/")[-1], "url": href})
            logger.info("Found %s volume links in Policy Manual", len(volumes))
            return volumes
        except Exception as e:
            logger.error("Failed to scrape policy manual index: %s", e)
            return []

    def discover_chapter_links(self, volume_url: str, html: str | None = None) -> list[dict]:
        """Find chapter/part links under a volume page."""
        try:
            if html is None:
                resp = self.client.get(volume_url)
                resp.raise_for_status()
                html = resp.text
            soup = BeautifulSoup(html, "lxml")
            links = []
            seen = set()
            for link in soup.select("a[href*='/policy-manual/']"):
                href = self._normalize_url(link.get("href", ""))
                title = link.get_text(strip=True)
                if not href or href == self._normalize_url(volume_url) or href in seen:
                    continue
                # Prefer chapter/part pages, skip pure anchors and the index.
                path = urlparse(href).path
                if "/policy-manual/" not in path or path.rstrip("/").endswith("policy-manual"):
                    continue
                seen.add(href)
                links.append({"title": title or path.split("/")[-1], "url": href})
            return links
        except Exception as e:
            logger.warning("Chapter discovery failed for %s: %s", volume_url, e)
            return []

    def scrape_page(
        self,
        url: str,
        doc_type: str = "policy",
        *,
        volume: str = "",
        part: str = "",
        chapter: str = "",
        source: str = "USCIS Policy Manual",
    ) -> list[ScrapedDocument]:
        """Scrape a single USCIS page and chunk it."""
        url = self._normalize_url(url)
        if not url or url in self._visited:
            return []
        self._visited.add(url)
        try:
            resp = self.client.get(url)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "lxml")

            content_div = (
                soup.select_one("div.field--name-body")
                or soup.select_one("div#region-content")
                or soup.select_one("article")
                or soup.select_one("main")
            )
            if not content_div:
                logger.warning("No content found at %s", url)
                return []

            title_el = soup.select_one("h1")
            title_text = title_el.get_text(strip=True) if title_el else "Untitled"
            full_text = self._clean_text(content_div)
            if len(full_text) < 50:
                return []

            effective_date = self._extract_effective_date(soup)
            scraped_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            vol = volume or self._volume_label(title_text, url)
            chap = chapter or title_text

            documents = []
            for i, chunk in enumerate(self._chunk_text(full_text)):
                documents.append(
                    ScrapedDocument(
                        id=self._make_id(f"{url}_{i}"),
                        title=title_text,
                        content=chunk,
                        source=source,
                        section=chap,
                        url=url,
                        doc_type=doc_type,
                        volume=vol,
                        part=part,
                        chapter=chap,
                        effective_date=effective_date,
                        scraped_at=scraped_at,
                        corpus_origin="scraped",
                    )
                )
            logger.info("Scraped %s chunks from: %s", len(documents), title_text)
            return documents
        except Exception as e:
            logger.error("Failed to scrape %s: %s", url, e)
            return []

    def scrape_form_instructions(self, form_numbers: list[str] | None = None) -> list[ScrapedDocument]:
        if form_numbers is None:
            form_numbers = [
                "i-129", "i-130", "i-140", "i-485", "i-765",
                "i-131", "i-539", "i-864", "i-693",
                "i-751", "i-90", "n-400", "i-765",
            ]
        all_docs = []
        for form in form_numbers:
            url = f"{USCIS_BASE}/{form}"
            logger.info("Scraping form: %s", form)
            docs = self.scrape_page(
                url,
                doc_type="form_instruction",
                source="USCIS Form Instructions",
                chapter=form.upper(),
            )
            for d in docs:
                d.section = f"Form {form.upper()}"
            all_docs.extend(docs)
            time.sleep(self.delay_seconds)
        return all_docs

    def scrape_policy_manual(
        self,
        max_volumes: int | None = None,
        max_chapters_per_volume: int | None = None,
        max_chapters: int | None = None,
        deep: bool = True,
        volume_numbers: list[int] | None = None,
    ) -> list[ScrapedDocument]:
        """Scrape Policy Manual volumes and optionally nested chapters.

        Args:
            max_volumes: Cap on number of volume index pages (after filtering).
            max_chapters_per_volume: Cap chapters discovered under each volume.
            max_chapters: Global cap on chapter pages scraped (safety valve).
            deep: When True, discover and scrape chapter links under each volume.
            volume_numbers: If set, only volumes whose URL/title match these numbers
                (e.g. [6, 7, 8, 9, 12]). Default keeps common immigration volumes.
        """
        volumes = self.scrape_policy_manual_index()
        if volume_numbers is None:
            volume_numbers = [6, 7, 8, 9, 12]
        if volume_numbers:
            wanted = set(volume_numbers)
            filtered = []
            for vol in volumes:
                m = re.search(r"volume[- ]?(\d+)", f"{vol['title']} {vol['url']}", re.I)
                if m and int(m.group(1)) in wanted:
                    filtered.append(vol)
            # If index scrape failed or naming differs, fall back to constructing URLs.
            if not filtered and wanted:
                for n in sorted(wanted):
                    filtered.append(
                        {
                            "title": f"Volume {n}",
                            "url": f"{USCIS_BASE}/policy-manual/volume-{n}",
                        }
                    )
            volumes = filtered
        if max_volumes is not None:
            volumes = volumes[:max_volumes]

        all_documents: list[ScrapedDocument] = []
        chapters_scraped = 0
        for vol in volumes:
            vol_label = self._volume_label(vol["title"], vol["url"])
            logger.info("Scraping volume: %s", vol_label)
            vol_docs = self.scrape_page(vol["url"], volume=vol_label, chapter=vol["title"])
            all_documents.extend(vol_docs)
            time.sleep(self.delay_seconds)

            if not deep:
                continue
            chapters = self.discover_chapter_links(vol["url"])
            if max_chapters_per_volume is not None:
                chapters = chapters[:max_chapters_per_volume]
            for ch in chapters:
                if max_chapters is not None and chapters_scraped >= max_chapters:
                    logger.info("Reached max_chapters=%s; stopping chapter scrape", max_chapters)
                    return all_documents
                docs = self.scrape_page(
                    ch["url"],
                    volume=vol_label,
                    chapter=ch["title"],
                )
                all_documents.extend(docs)
                chapters_scraped += 1
                time.sleep(self.delay_seconds)
        return all_documents

    def save_documents(self, documents: list[ScrapedDocument], filename: str):
        output_path = RAW_DATA_DIR / f"{filename}.json"
        RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)
        data = [asdict(doc) for doc in documents]
        output_path.write_text(json.dumps(data, indent=2))
        logger.info("Saved %s documents to %s", len(documents), output_path)

    def write_manifest(self, documents: list[ScrapedDocument], filename: str = "corpus_manifest.json"):
        by_type: dict[str, int] = {}
        for d in documents:
            by_type[d.doc_type] = by_type.get(d.doc_type, 0) + 1
        manifest = {
            "corpus_origin": "scraped",
            "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "document_count": len(documents),
            "by_doc_type": by_type,
            "unique_urls": len({d.url for d in documents}),
        }
        path = RAW_DATA_DIR / filename
        path.write_text(json.dumps(manifest, indent=2))
        logger.info("Wrote corpus manifest to %s", path)
        return path

    def run_full_scrape(
        self,
        max_volumes: int | None = None,
        max_chapters_per_volume: int | None = 25,
        deep: bool = True,
        include_forms: bool = True,
    ) -> list[ScrapedDocument]:
        logger.info("=" * 60)
        logger.info("Starting USCIS data scrape (deep=%s, max_volumes=%s)", deep, max_volumes)
        logger.info("=" * 60)

        all_documents = self.scrape_policy_manual(
            max_volumes=max_volumes,
            max_chapters_per_volume=max_chapters_per_volume,
            deep=deep,
        )
        if include_forms:
            all_documents.extend(self.scrape_form_instructions())

        self.save_documents(all_documents, "uscis_all_documents")
        self.write_manifest(all_documents)
        logger.info("Scraping complete! Total documents: %s", len(all_documents))
        return all_documents


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    scraper = USCISPolicyScraper()
    scraper.run_full_scrape()
