"""Retrieval models shared by the retriever and the agent tools."""

import re
from datetime import date
from uuid import UUID

from pydantic import BaseModel, Field

MAX_PASSAGE_EXCERPT_CHARS = 800
MAX_AGENT_OUTPUT_CHARS = 20_000

_SPACE_RUN = re.compile(r"[ \t]+")
_DASH_RUN = re.compile(r"-{3,}")


class SearchFilters(BaseModel):
    ticker: str | None = None
    fiscal_years: list[int] | None = None


class RetrievedPassage(BaseModel):
    chunk_id: UUID
    document_id: UUID
    chunk_index: int
    content: str
    page: int | None
    section: str | None
    fusion_score: float
    ticker: str
    company_name: str
    form: str
    fiscal_year: int
    reference_period: date
    source_url: str
    neighbors: list["RetrievedPassage"] = Field(default_factory=list)


def compact_text(text: str) -> str:
    """Chunk text as shown to the agent: Markdown table padding squeezed out.

    Docling pads table cells to column width, so a wide table can be mostly
    spaces and `-----` separators — a 14k-char chunk whose first 800 chars
    are header padding. Rows and line breaks are kept.
    """
    return _DASH_RUN.sub("---", _SPACE_RUN.sub(" ", text)).strip()


def normalize_for_match(text: str) -> str:
    """Canonical form for verbatim-quote checks.

    normalize_for_match(compact_text(x)) == normalize_for_match(x), so a quote
    copied from compacted tool output still matches the stored chunk text.
    """
    return " ".join(_DASH_RUN.sub("---", text).split())


def _excerpt(content: str, *, full_text: bool) -> str:
    excerpt = compact_text(content)
    if not full_text and len(excerpt) > MAX_PASSAGE_EXCERPT_CHARS:
        return excerpt[:MAX_PASSAGE_EXCERPT_CHARS] + "..."
    return excerpt


def _format_passage(passage: RetrievedPassage, *, full_text: bool) -> str:
    page = f" p.{passage.page}" if passage.page is not None else ""
    section = f" ({passage.section})" if passage.section else ""
    header = f"{passage.ticker} {passage.form} FY{passage.fiscal_year}{page}{section}"
    lines = [f"{header} [{passage.chunk_id}]: {_excerpt(passage.content, full_text=full_text)}"]
    for neighbor in passage.neighbors:
        excerpt = _excerpt(neighbor.content, full_text=full_text)
        lines.append(f"  neighbor idx={neighbor.chunk_index} [{neighbor.chunk_id}]: {excerpt}")
    return "\n".join(lines)


def format_passages_for_agent(passages: list[RetrievedPassage], *, full_text: bool = False) -> str:
    """Bounded, grep-style text for PydanticAI tool responses.

    Search results show capped excerpts; read tools pass `full_text=True`,
    since reading the whole chunk is the point of calling them.
    """
    if not passages:
        return "No matching passages found in the filing corpus."

    output = "\n\n".join(_format_passage(p, full_text=full_text) for p in passages)
    if len(output) > MAX_AGENT_OUTPUT_CHARS:
        output = output[:MAX_AGENT_OUTPUT_CHARS] + "\n... truncated. Narrow the query or read specific chunks."
    return output
