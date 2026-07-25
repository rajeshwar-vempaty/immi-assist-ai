"""Map natural-language / tool requests onto USCIS processing-time lookups.

Prefers the structured live/snapshot cascade (uscis_times_service) so chat and
POST /timeline stop inventing wait times from RAG prose alone.
"""

from __future__ import annotations

import re
from typing import Any

from app.services import uscis_times_service as uscis

USCIS_FORM_RE = re.compile(r"\b((?:I|N|G|AR|EOIR|DS)[-\s]?\d{1,4}[A-Z]?)\b", re.IGNORECASE)

# Visa / topic keywords → (form_id, category_id, office_id)
_TOPIC_MAP: list[tuple[tuple[str, ...], tuple[str, str, str]]] = [
    (("stem opt", "stem-opt"), ("I-765", "c3", "scops")),
    (("opt", "f-1 opt", "f1 opt", "ead"), ("I-765", "c3", "scops")),
    (("h-4 ead", "h4 ead", "c26"), ("I-765", "c26", "scops")),
    (("h-1b", "h1b"), ("I-129", "h-1b", "scops")),
    (("h-2a", "h2a"), ("I-129", "h-2a", "scops")),
    (("h-2b", "h2b"), ("I-129", "h-2b", "scops")),
    (("l-1", "l1a", "l1b", "l-1a", "l-1b"), ("I-129", "l-1", "scops")),
    (("o-1", "o1"), ("I-129", "o-1", "scops")),
    (("tn ", " tn", "nafta"), ("I-129", "tn", "scops")),
    (("treaty", "e-2", "e2 ", "e-1"), ("I-129", "e-treaty", "scops")),
    (("niw",), ("I-140", "eb2-niw", "scops")),
    (("eb-1", "eb1", "extraordinary"), ("I-140", "eb1-extraordinary", "scops")),
    (("eb-2", "eb2", "advanced degree"), ("I-140", "eb2-advanced", "scops")),
    (("eb-3", "eb3"), ("I-140", "eb3-skilled", "scops")),
    (("i-140", "i140"), ("I-140", "eb2-advanced", "scops")),
    (("i-485", "i485", "green card", "adjustment"), ("I-485", "employment", "scops")),
    (("i-130", "i130", "family petition"), ("I-130", "immediate-relative", "scops")),
    (("n-400", "n400", "naturalization", "citizenship"), ("N-400", "standard", "field-median")),
    (("i-539", "i539", "change of status", "extend stay"), ("I-539", "extend-b", "scops")),
    (("i-751", "i751"), ("I-751", "joint", "scops")),
    (("i-90", "i90", "green card renewal"), ("I-90", "initial", "scops")),
    (("i-131", "i131", "advance parole", "travel document"), ("I-131", "advance-parole", "scops")),
    (("i-129", "i129"), ("I-129", "h-1b", "scops")),
    (("i-765", "i765"), ("I-765", "c3", "scops")),
]


def normalize_form_number(form_number: str) -> str:
    compact = re.sub(r"[-\s]", "", form_number).upper()
    match = re.fullmatch(r"([A-Z]+)(\d{1,4})([A-Z]?)", compact)
    if not match:
        return form_number.strip()
    prefix, number, suffix = match.groups()
    return f"{prefix}-{number}{suffix}"


def extract_form_number(text: str | None) -> str | None:
    if not text:
        return None
    match = USCIS_FORM_RE.search(text)
    if not match:
        return None
    return normalize_form_number(match.group(1))


def resolve_lookup_keys(
    *,
    message: str = "",
    form_type: str | None = None,
    category: str | None = None,
    service_center: str | None = None,
) -> tuple[str, str, str] | None:
    """Best-effort (form, category, office) for the USCIS cascade."""
    blob = " ".join(filter(None, [message, form_type, category, service_center])).lower()
    if not blob.strip():
        return None

    mapped: tuple[str, str, str] | None = None
    for keywords, triple in _TOPIC_MAP:
        if any(k in blob for k in keywords):
            mapped = triple
            break

    form = extract_form_number(form_type) or extract_form_number(message)
    if mapped:
        form = form or mapped[0]
        cat = mapped[1]
        office = mapped[2]
    elif form:
        # Form known but no topic — pick a common category/office for that form.
        defaults = {
            "I-129": ("h-1b", "scops"),
            "I-140": ("eb2-advanced", "scops"),
            "I-485": ("employment", "scops"),
            "I-765": ("c3", "scops"),
            "I-130": ("immediate-relative", "scops"),
            "N-400": ("standard", "field-median"),
            "I-539": ("extend-b", "scops"),
            "I-751": ("joint", "scops"),
            "I-90": ("initial", "scops"),
            "I-131": ("advance-parole", "scops"),
        }
        pair = defaults.get(form)
        if not pair:
            return None
        cat, office = pair
    else:
        return None

    # Explicit category from API (timeline tool) if it already looks like a cascade id.
    if category and re.fullmatch(r"[a-z0-9\-]+", category.strip().lower()):
        cat = category.strip().lower()

    if service_center:
        sc = service_center.lower()
        if "national benefits" in sc or sc == "nbc":
            office = "nbc"
        elif "field" in sc:
            office = "field-median"
        elif "scops" in sc or "service center operations" in sc:
            office = "scops"

    return form, cat, office


def format_official_block(pt: dict[str, Any]) -> str:
    months = pt.get("months")
    if months is None:
        return ""
    source = pt.get("source", "snapshot")
    as_of = pt.get("as_of") or pt.get("publication_date") or "unknown"
    url = pt.get("uscis_url") or uscis.USCIS_PAGE_URL
    return (
        "OFFICIAL USCIS PROCESSING TIME (authoritative — do not invent different months):\n"
        f"- Form: {pt.get('form')}\n"
        f"- Category id: {pt.get('category')}\n"
        f"- Office id: {pt.get('office')}\n"
        f"- 80% of cases completed within: {months} months\n"
        f"- Data source: {source}\n"
        f"- As of / published: {as_of}\n"
        f"- Verify: {url}\n"
        "Explain this figure in plain language. If the user's form/office is uncertain, say so."
    )


async def lookup_official_time(
    *,
    message: str = "",
    form_type: str | None = None,
    category: str | None = None,
    service_center: str | None = None,
) -> dict[str, Any] | None:
    keys = resolve_lookup_keys(
        message=message,
        form_type=form_type,
        category=category,
        service_center=service_center,
    )
    if not keys:
        return None
    form, cat, office = keys
    pt = await uscis.get_processing_time(form, cat, office)
    if pt.get("months") is None:
        return None
    return pt
