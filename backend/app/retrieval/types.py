"""Retrieval models shared by the retriever and the agent tools."""

from datetime import date
from uuid import UUID

from pydantic import BaseModel, Field

MAX_PASSAGE_EXCERPT_CHARS = 800
MAX_AGENT_OUTPUT_CHARS = 12_000


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


def _excerpt(content: str) -> str:
    excerpt = content.strip()
    if len(excerpt) > MAX_PASSAGE_EXCERPT_CHARS:
        return excerpt[:MAX_PASSAGE_EXCERPT_CHARS] + "..."
    return excerpt


def _format_passage(passage: RetrievedPassage) -> str:
    page = f" p.{passage.page}" if passage.page is not None else ""
    section = f" ({passage.section})" if passage.section else ""
    header = f"{passage.ticker} {passage.form} FY{passage.fiscal_year}{page}{section}"
    lines = [f"{header} [{passage.chunk_id}]: {_excerpt(passage.content)}"]
    for neighbor in passage.neighbors:
        lines.append(f"  neighbor idx={neighbor.chunk_index} [{neighbor.chunk_id}]: {_excerpt(neighbor.content)}")
    return "\n".join(lines)


def format_passages_for_agent(passages: list[RetrievedPassage]) -> str:
    """Bounded, grep-style text for PydanticAI tool responses."""
    if not passages:
        return "No matching passages found in the filing corpus."

    output = "\n\n".join(_format_passage(p) for p in passages)
    if len(output) > MAX_AGENT_OUTPUT_CHARS:
        output = output[:MAX_AGENT_OUTPUT_CHARS] + "\n... truncated. Narrow the query or read specific chunks."
    return output
