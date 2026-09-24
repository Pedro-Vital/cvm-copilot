"""Bounded agent tools over the retrieval layer.

Docstrings are the tool descriptions the model sees. Bad input comes back as
an "Error: ..." string rather than an exception so the agent can correct
itself and retry. Every returned passage is registered in the turn registry,
which is the citation allowlist.
"""

import time
from uuid import UUID

import structlog
from pydantic_ai import RunContext

from app.assistant.deps import DocumentAgentDeps
from app.retrieval.types import (
    RetrievedPassage,
    SearchFilters,
    format_passages_for_agent,
)

# Past this, a model hunting for a perfect table keeps searching until it
# hits the request limit and the turn fails; stopping it here makes it answer
# with what it has and name the gaps instead.
MAX_SEARCHES_PER_TURN = 8
MAX_SURROUNDING_RADIUS = 3
MAX_READ_CHUNKS = 10

logger = structlog.get_logger(__name__)


def _parse_chunk_ids(chunk_ids: list[str]) -> list[UUID] | str:
    parsed: list[UUID] = []
    for chunk_id in chunk_ids:
        try:
            parsed.append(UUID(chunk_id))
        except ValueError:
            return f"Error: invalid chunk_id {chunk_id!r}. Use the UUID shown in brackets in search results."
    return parsed


def _register_and_format(
    ctx: RunContext[DocumentAgentDeps],
    tool: str,
    started: float,
    passages: list[RetrievedPassage],
    *,
    full_text: bool = False,
    **log_fields,
) -> str:
    ctx.deps.registry.register_many(passages)
    logger.info(
        "agent_tool",
        tool=tool,
        results=len(passages),
        duration_ms=round((time.perf_counter() - started) * 1000),
        **log_fields,
    )
    return format_passages_for_agent(passages, full_text=full_text)


async def search_filings(
    ctx: RunContext[DocumentAgentDeps],
    query: str,
    ticker: str | None = None,
    fiscal_years: list[int] | None = None,
) -> str:
    """Hybrid (semantic + keyword) search over CVM DFP filings. Returns ranked passages with chunk ids.

    Write the query in Portuguese, using the terms the filing itself would use
    (e.g. "receita líquida por segmento", "provisões para contingências").
    Filter by `ticker` (ITUB4, MGLU3, SUZB3, VALE3, WEGE3) and `fiscal_years`
    (2021–2025) whenever the question names them. When comparing companies,
    call this once per ticker so every company gets its own results.
    """
    if ctx.deps.searches_run >= MAX_SEARCHES_PER_TURN:
        return (
            f"Error: search limit reached ({MAX_SEARCHES_PER_TURN} searches). Do not search again. "
            "Answer now with the passages already retrieved, and state which items or years were not found."
        )
    ctx.deps.searches_run += 1

    started = time.perf_counter()
    filters = SearchFilters(ticker=ticker, fiscal_years=fiscal_years)
    passages = await ctx.deps.retriever.search(query, filters=filters)
    return _register_and_format(
        ctx, "search_filings", started, passages, query=query, ticker=ticker, fiscal_years=fiscal_years
    )


async def read_chunks(ctx: RunContext[DocumentAgentDeps], chunk_ids: list[str]) -> str:
    """Read the full text of one or more chunks by id (up to 10 per call).

    Use when a search excerpt was truncated ("...") and you need the rest,
    e.g. the full rows of a table.
    """
    if not chunk_ids:
        return "Error: chunk_ids must include at least one id."
    if len(chunk_ids) > MAX_READ_CHUNKS:
        return f"Error: at most {MAX_READ_CHUNKS} chunk_ids per call."
    parsed = _parse_chunk_ids(chunk_ids)
    if isinstance(parsed, str):
        return parsed

    started = time.perf_counter()
    passages = await ctx.deps.retriever.read_chunks(parsed)
    if not passages:
        return "Error: none of the requested chunks were found."
    return _register_and_format(ctx, "read_chunks", started, passages, full_text=True, chunk_ids=chunk_ids)


async def read_surrounding_chunks(ctx: RunContext[DocumentAgentDeps], chunk_id: str, radius: int = 1) -> str:
    """Read a chunk plus up to `radius` (1–3) chunks before and after it in the same filing.

    Use when a passage starts or ends mid-table or mid-note and the search
    results' neighbors don't cover enough.
    """
    if not 1 <= radius <= MAX_SURROUNDING_RADIUS:
        return f"Error: radius must be between 1 and {MAX_SURROUNDING_RADIUS}."
    parsed = _parse_chunk_ids([chunk_id])
    if isinstance(parsed, str):
        return parsed

    started = time.perf_counter()
    passages = await ctx.deps.retriever.read_surrounding(parsed[0], radius)
    if not passages:
        return f"Error: chunk {chunk_id} not found."
    return _register_and_format(
        ctx, "read_surrounding_chunks", started, passages, full_text=True, chunk_id=chunk_id, radius=radius
    )
