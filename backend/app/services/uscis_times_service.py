"""Live USCIS case processing times with cached-snapshot fallback.

Proxies the same API the official USCIS processing-times page uses
(https://egov.uscis.gov/processing-times/). That API sits behind Cloudflare
bot protection and rejects many datacenter IPs, so every lookup falls back
to a bundled snapshot of published USCIS figures when the live call fails.
Responses always say which source they came from.
"""

import json
import logging
import time
from pathlib import Path

import httpx

logger = logging.getLogger(__name__)

USCIS_API_BASE = "https://egov.uscis.gov/processing-times/api"
USCIS_PAGE_URL = "https://egov.uscis.gov/processing-times/"

_BROWSER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"
    ),
    "Accept": "application/json",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": USCIS_PAGE_URL,
}

_LIVE_TTL_SECONDS = 12 * 3600
_FAILURE_BACKOFF_SECONDS = 10 * 60

_SNAPSHOT_PATH = Path(__file__).resolve().parent.parent / "data" / "uscis_processing_times_snapshot.json"

_cache: dict[str, tuple[float, object]] = {}
_live_blocked_until = 0.0


def _load_snapshot() -> dict:
    key = "__snapshot__"
    hit = _cache.get(key)
    if hit:
        return hit[1]
    data = json.loads(_SNAPSHOT_PATH.read_text())
    _cache[key] = (float("inf"), data)
    return data


async def _fetch_live(path: str):
    """Fetch a USCIS API path, or None when unreachable/blocked."""
    global _live_blocked_until
    now = time.time()
    cache_key = f"live:{path}"
    hit = _cache.get(cache_key)
    if hit and hit[0] > now:
        return hit[1]
    if now < _live_blocked_until:
        return None
    try:
        async with httpx.AsyncClient(headers=_BROWSER_HEADERS, timeout=8.0, follow_redirects=True) as client:
            resp = await client.get(f"{USCIS_API_BASE}{path}")
        if resp.status_code != 200 or "application/json" not in resp.headers.get("content-type", ""):
            raise ValueError(f"USCIS API returned {resp.status_code}")
        data = resp.json()
        _cache[cache_key] = (now + _LIVE_TTL_SECONDS, data)
        return data
    except Exception as exc:  # noqa: BLE001 - any live failure falls back to snapshot
        logger.info("USCIS live API unavailable (%s); using snapshot fallback", exc)
        _live_blocked_until = now + _FAILURE_BACKOFF_SECONDS
        return None


def _first_list_of_dicts(payload, *key_hints):
    """Depth-first search for the first list of dicts under keys matching hints."""
    stack = [payload]
    while stack:
        node = stack.pop()
        if isinstance(node, dict):
            for key, value in node.items():
                if isinstance(value, list) and value and isinstance(value[0], dict):
                    if not key_hints or any(h in key.lower() for h in key_hints):
                        return value
                stack.append(value)
        elif isinstance(node, list):
            stack.extend(node)
    return None


def _pick(d: dict, *candidates, default=""):
    for c in candidates:
        if c in d and d[c] not in (None, ""):
            return d[c]
    return default


async def get_forms() -> dict:
    live = await _fetch_live("/forms")
    if live:
        rows = _first_list_of_dicts(live, "forms") or []
        forms = [
            {
                "id": _pick(r, "form_name", "form", "id"),
                "description": _pick(r, "form_description_en", "form_description", "description"),
            }
            for r in rows
        ]
        forms = [f for f in forms if f["id"]]
        if forms:
            return {"source": "live", "forms": forms}
    snap = _load_snapshot()
    return {"source": "snapshot", "as_of": snap["as_of"], "forms": snap["forms"]}


async def get_categories(form_id: str) -> dict:
    live = await _fetch_live(f"/formtypes/{form_id}")
    if live:
        rows = _first_list_of_dicts(live, "form_types", "subtypes") or []
        cats = [
            {
                "id": _pick(r, "form_type", "subtype", "id"),
                "description": _pick(
                    r, "form_type_description_en", "subtype_info_en", "description"
                ),
            }
            for r in rows
        ]
        cats = [c for c in cats if c["id"]]
        if cats:
            return {"source": "live", "categories": cats}
    snap = _load_snapshot()
    return {
        "source": "snapshot",
        "as_of": snap["as_of"],
        "categories": snap["categories"].get(form_id, []),
    }


async def get_offices(form_id: str, category_id: str) -> dict:
    live = await _fetch_live(f"/formoffices/{form_id}/{category_id}")
    if live:
        rows = _first_list_of_dicts(live, "offices") or []
        offices = [
            {
                "id": _pick(r, "office_code", "code", "id"),
                "description": _pick(r, "office_description", "description", "name"),
            }
            for r in rows
        ]
        offices = [o for o in offices if o["id"]]
        if offices:
            return {"source": "live", "offices": offices}
    snap = _load_snapshot()
    offices = snap["offices"].get(f"{form_id}|{category_id}", snap["offices"]["default"])
    return {"source": "snapshot", "as_of": snap["as_of"], "offices": offices}


def _extract_live_months(payload) -> tuple[float | None, str]:
    """Pull the '80% completed within' months value out of the live payload."""
    publication = ""
    stack = [payload]
    ranges = []
    while stack:
        node = stack.pop()
        if isinstance(node, dict):
            if not publication:
                publication = _pick(node, "publication_date", default="")
            rng = node.get("range")
            if isinstance(rng, list) and rng and isinstance(rng[0], dict):
                ranges.append(rng)
            stack.extend(node.values())
        elif isinstance(node, list):
            stack.extend(node)
    for rng in ranges:
        values = [r.get("value") for r in rng if isinstance(r.get("value"), (int, float))]
        if values:
            return float(max(values)), publication
    return None, publication


async def get_processing_time(form_id: str, category_id: str, office_id: str) -> dict:
    live = await _fetch_live(f"/processingtime/{form_id}/{office_id}/{category_id}")
    if live:
        months, publication = _extract_live_months(live)
        if months is not None:
            return {
                "source": "live",
                "form": form_id,
                "category": category_id,
                "office": office_id,
                "months": months,
                "publication_date": publication,
                "uscis_url": USCIS_PAGE_URL,
            }
    snap = _load_snapshot()
    months = snap["times"].get(f"{form_id}|{category_id}|{office_id}")
    return {
        "source": "snapshot",
        "as_of": snap["as_of"],
        "form": form_id,
        "category": category_id,
        "office": office_id,
        "months": months,
        "uscis_url": USCIS_PAGE_URL,
    }
