"""
Citation formatter — Formats source citations for responses.
"""


def format_citations(sources: list[str]) -> str:
    """Format a list of sources into a citation block."""
    if not sources:
        return ""

    citation_lines = []
    for i, source in enumerate(sources, 1):
        citation_lines.append(f"[{i}] {source}")

    return "\n\n**Sources:**\n" + "\n".join(citation_lines)


def format_inline_citation(source_name: str, index: int) -> str:
    """Create an inline citation reference."""
    return f"[Source: {source_name}]"
