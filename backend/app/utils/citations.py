"""
Citation formatter — Formats source citations for responses.
"""


def format_citations(sources: list) -> str:
    """Format a list of sources (strings or {label, url} dicts) into a citation block.

    Sources with a URL are emitted as markdown links so clients render hyperlinks.
    """
    if not sources:
        return ""

    citation_lines = []
    for i, source in enumerate(sources, 1):
        if isinstance(source, dict):
            label = source.get("label", "USCIS Document")
            url = source.get("url", "")
            entry = f"[{label}]({url})" if url else label
        else:
            entry = str(source)
        citation_lines.append(f"[{i}] {entry}")

    return "\n\n**Sources:**\n" + "\n".join(citation_lines)


def format_inline_citation(source_name: str, index: int) -> str:
    """Create an inline citation reference."""
    return f"[Source: {source_name}]"
