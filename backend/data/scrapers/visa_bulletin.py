"""
Visa Bulletin scraper — Department of State monthly priority dates.

Primary page: https://travel.state.gov/content/travel/en/legal/visa-law0/visa-bulletin.html

Produces:
- Structured JSON (categories + date cells when parseable)
- RAG-friendly paragraph chunks for the policy collection
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
from datetime import datetime, timezone
from pathlib import Path

import httpx
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

BULLETIN_INDEX_URL = (
    "https://travel.state.gov/content/travel/en/legal/visa-law0/visa-bulletin.html"
)
RAW_DATA_DIR = Path(__file__).parent.parent / "raw"


def _make_id(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()[:16]


def _clean(text: str) -> str:
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


class VisaBulletinScraper:
    def __init__(self, delay: float = 0.0):
        self.delay = delay
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

    def scrape_latest(self) -> dict:
        """Alias for scrape() — latest bulletin from the index page."""
        return self.scrape()

    def to_rag_documents(self, bulletin: dict | None = None) -> list[dict]:
        """Return RAG paragraph dicts from a structured bulletin payload."""
        if bulletin is None:
            bulletin = self.scrape_latest()
        docs = bulletin.get("rag_documents") or []
        return list(docs)

    def latest_bulletin_url(self, html: str | None = None) -> str | None:
        if html is None:
            resp = self.client.get(BULLETIN_INDEX_URL)
            resp.raise_for_status()
            html = resp.text
        soup = BeautifulSoup(html, "lxml")
        # Prefer links that look like the current month bulletin.
        candidates = []
        for a in soup.select("a[href*='visa-bulletin']"):
            href = a.get("href", "")
            text = a.get_text(" ", strip=True)
            if not href:
                continue
            if href.startswith("/"):
                href = "https://travel.state.gov" + href
            if re.search(r"visa-bulletin-for-", href, re.I) or re.search(
                r"Visa Bulletin for", text, re.I
            ):
                candidates.append((href, text))
        if not candidates:
            return BULLETIN_INDEX_URL
        return candidates[0][0]

    def scrape(self, url: str | None = None) -> dict:
        index_html = None
        if url is None:
            index_resp = self.client.get(BULLETIN_INDEX_URL)
            index_resp.raise_for_status()
            index_html = index_resp.text
            url = self.latest_bulletin_url(index_html) or BULLETIN_INDEX_URL

        logger.info("Scraping Visa Bulletin: %s", url)
        resp = self.client.get(url)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "lxml")

        title_el = soup.select_one("h1")
        title = title_el.get_text(strip=True) if title_el else "Visa Bulletin"
        month_match = re.search(
            r"Visa Bulletin for ([A-Za-z]+ \d{4})", title + " " + soup.get_text(" ", strip=True)
        )
        bulletin_month = month_match.group(1) if month_match else ""

        content_div = (
            soup.select_one("div.entry-content")
            or soup.select_one("div#region-content")
            or soup.select_one("article")
            or soup.select_one("main")
            or soup.body
        )
        full_text = _clean(content_div.get_text("\n", strip=True) if content_div else "")

        tables = []
        for table in soup.select("table")[:8]:
            headers = [th.get_text(" ", strip=True) for th in table.select("tr th")]
            if not headers:
                first = table.select_one("tr")
                if first:
                    headers = [c.get_text(" ", strip=True) for c in first.select("td")]
            rows = []
            for tr in table.select("tr")[1:]:
                cells = [td.get_text(" ", strip=True) for td in tr.select("td")]
                if cells:
                    rows.append(cells)
            if rows:
                tables.append({"headers": headers, "rows": rows[:40]})

        scraped_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        structured = {
            "source": "Visa Bulletin",
            "title": title,
            "bulletin_month": bulletin_month,
            "url": url,
            "scraped_at": scraped_at,
            "tables": tables,
            "summary_text": full_text[:4000],
        }

        # RAG paragraphs — split summary into digestible chunks with metadata.
        paragraphs = []
        intro = (
            f"{title}. The Department of State Visa Bulletin shows when immigrant visa numbers "
            f"are available by preference category and country of chargeability. "
            f"A priority date must be current for I-485 filing or consular processing."
        )
        if bulletin_month:
            intro = f"Visa Bulletin for {bulletin_month}. " + intro
        chunks = [intro]
        # Keep table snapshots as text for RAG.
        for i, table in enumerate(tables[:4], 1):
            header_line = " | ".join(table.get("headers") or [])
            row_lines = [" | ".join(r) for r in (table.get("rows") or [])[:12]]
            chunk = f"{title} — table {i}\n{header_line}\n" + "\n".join(row_lines)
            if len(chunk) > 80:
                chunks.append(chunk)
        if full_text:
            # Additional narrative slices.
            for i in range(0, min(len(full_text), 6000), 1400):
                piece = full_text[i : i + 1400].strip()
                if len(piece) > 80:
                    chunks.append(piece)

        for i, content in enumerate(chunks):
            paragraphs.append(
                {
                    "id": _make_id(f"{url}_{i}"),
                    "content": content,
                    "source": "Visa Bulletin",
                    "section": bulletin_month or title,
                    "doc_type": "visa_bulletin",
                    "url": url,
                    "volume": "",
                    "part": "",
                    "chapter": bulletin_month or title,
                    "effective_date": bulletin_month,
                    "scraped_at": scraped_at,
                    "corpus_origin": "scraped",
                }
            )

        structured["rag_documents"] = paragraphs
        return structured

    def save(self, data: dict) -> Path:
        RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)
        path = RAW_DATA_DIR / "visa_bulletin.json"
        path.write_text(json.dumps(data, indent=2))
        logger.info(
            "Saved Visa Bulletin (%s RAG chunks) to %s",
            len(data.get("rag_documents") or []),
            path,
        )
        return path


def scrape_and_save() -> dict:
    scraper = VisaBulletinScraper()
    data = scraper.scrape()
    scraper.save(data)
    return data


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    scrape_and_save()
