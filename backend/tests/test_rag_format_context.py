"""RAG format_context citation excerpts."""

from app.services.rag_service import RAGService


def test_format_context_includes_excerpt_for_each_source():
    # Bypass __init__ (would need OpenAI + Chroma).
    rag = object.__new__(RAGService)
    docs = [
        {
            "document": "H-1B specialty occupation requires a bachelor's degree or equivalent. " * 8,
            "metadata": {
                "source": "USCIS Policy Manual",
                "section": "H-1B",
                "url": "https://www.uscis.gov/h-1b",
            },
        },
        {
            "document": "Priority dates must be current per the Visa Bulletin.",
            "metadata": {
                "source": "Visa Bulletin",
                "section": "July 2026",
                "url": "https://travel.state.gov/visa-bulletin",
            },
        },
    ]
    context, sources = rag.format_context(docs)
    assert "H-1B" in context
    assert len(sources) == 2
    assert sources[0]["url"].endswith("/h-1b")
    assert sources[0]["excerpt"]
    assert sources[0]["excerpt"].endswith("…") or len(sources[0]["excerpt"]) <= 280
    assert "Priority dates" in sources[1]["excerpt"]
    assert "excerpt" in sources[1]
