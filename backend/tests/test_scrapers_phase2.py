"""Unit tests for USCIS Policy Manual / Visa Bulletin scrapers (mocked HTML, no network)."""

from __future__ import annotations

from data.scrapers.uscis_policy import USCISPolicyScraper
from data.scrapers.visa_bulletin import VisaBulletinScraper


VOLUME_HTML = """
<html><body>
  <h1>Volume 6 - Immigrants</h1>
  <a href="/policy-manual/volume-6-part-e-chapter-1">Chapter 1 - Eligibility</a>
  <a href="/policy-manual/volume-6-part-e-chapter-2">Chapter 2 - Evidence</a>
  <a href="/policy-manual">Policy Manual Home</a>
</body></html>
"""

CHAPTER_HTML = """
<html><body>
  <h1>Chapter 1 - Eligibility</h1>
  <div class="field--name-body">
    <p>Current as of January 15, 2025</p>
    <p>An applicant must meet the eligibility requirements for classification as described
    in this chapter. Evidence should demonstrate each element of eligibility with primary
    documentation whenever available. Secondary evidence may be accepted when primary
    documentation is unavailable for reasons beyond the applicant's control.</p>
  </div>
</body></html>
"""

BULLETIN_INDEX_HTML = """
<html><body>
  <h1>Visa Bulletin</h1>
  <a href="/content/travel/en/legal/visa-law0/visa-bulletin/2025/visa-bulletin-for-june-2025.html">
    Visa Bulletin for June 2025
  </a>
  <a href="/content/travel/en/legal/visa-law0/visa-bulletin/2026/visa-bulletin-for-july-2026.html">
    Visa Bulletin for July 2026
  </a>
  <a href="/content/travel/en/legal/visa-law0/visa-bulletin/2026/visa-bulletin-for-may-2026.html">
    Visa Bulletin for May 2026
  </a>
</body></html>
"""

BULLETIN_PAGE_HTML = """
<html><body>
  <h1>Visa Bulletin for July 2026</h1>
  <div class="entry-content">
    <p>This bulletin summarizes the availability of immigrant numbers during July 2026.</p>
    <table>
      <tr><th>Employment-based</th><th>All Chargeability</th><th>China</th><th>India</th></tr>
      <tr><td>1st</td><td>C</td><td>15FEB22</td><td>01APR21</td></tr>
      <tr><td>2nd</td><td>15MAR23</td><td>01JUN20</td><td>01JAN12</td></tr>
    </table>
  </div>
</body></html>
"""


def test_discover_chapter_links_from_volume_html():
    scraper = USCISPolicyScraper(delay_seconds=0)
    links = scraper.discover_chapter_links(
        "https://www.uscis.gov/policy-manual/volume-6",
        html=VOLUME_HTML,
    )
    hrefs = [l["url"] for l in links]
    assert any("chapter-1" in h for h in hrefs)
    assert any("chapter-2" in h for h in hrefs)
    assert not any(h.rstrip("/").endswith("policy-manual") for h in hrefs)


def test_scrape_page_extracts_metadata(monkeypatch):
    scraper = USCISPolicyScraper(delay_seconds=0)

    class FakeResp:
        text = CHAPTER_HTML
        def raise_for_status(self):
            return None

    monkeypatch.setattr(scraper.client, "get", lambda url: FakeResp())
    docs = scraper.scrape_page(
        "https://www.uscis.gov/policy-manual/volume-6-part-e-chapter-1",
        volume="Volume 6",
        chapter="Chapter 1 - Eligibility",
    )
    assert docs
    d = docs[0]
    assert d.corpus_origin == "scraped"
    assert d.volume == "Volume 6"
    assert d.chapter == "Chapter 1 - Eligibility"
    assert "January 15, 2025" in d.effective_date
    assert "eligibility" in d.content.lower()
    assert d.scraped_at


def test_visa_bulletin_latest_url_from_index():
    vb = VisaBulletinScraper()
    url = vb.latest_bulletin_url(BULLETIN_INDEX_HTML)
    assert url is not None
    # Must pick chronologically latest (July 2026), not first link (June 2025).
    assert "visa-bulletin-for-july-2026" in url
    assert "june-2025" not in url
    assert "may-2026" not in url


def test_visa_bulletin_scrape_builds_rag_chunks(monkeypatch):
    vb = VisaBulletinScraper()

    class FakeResp:
        def __init__(self, text):
            self.text = text
        def raise_for_status(self):
            return None

    calls = {"n": 0}

    def fake_get(url):
        calls["n"] += 1
        if "visa-bulletin-for-july" in url:
            return FakeResp(BULLETIN_PAGE_HTML)
        return FakeResp(BULLETIN_INDEX_HTML)

    monkeypatch.setattr(vb.client, "get", fake_get)
    data = vb.scrape_latest()
    assert data["bulletin_month"] == "July 2026"
    assert data["tables"]
    rag = vb.to_rag_documents(data)
    assert len(rag) >= 2
    assert all(d["doc_type"] == "visa_bulletin" for d in rag)
    assert all(d["corpus_origin"] == "scraped" for d in rag)
    assert any("Employment-based" in d["content"] or "Visa Bulletin" in d["content"] for d in rag)
