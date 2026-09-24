from dataclasses import dataclass
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.assistant.deps import DocumentAgentDeps, TurnRegistry
from app.assistant.tools import (
    MAX_SEARCHES_PER_TURN,
    read_chunks,
    read_surrounding_chunks,
    search_filings,
)
from app.retrieval.types import SearchFilters


@dataclass
class FakeCtx:
    """Tools only touch `ctx.deps`, so a real RunContext isn't needed."""

    deps: DocumentAgentDeps


def make_ctx() -> FakeCtx:
    retriever = MagicMock(search=AsyncMock(), read_chunks=AsyncMock(), read_surrounding=AsyncMock())
    return FakeCtx(DocumentAgentDeps(retriever=retriever, registry=TurnRegistry(), user_id="u1", thread_id="t1"))


@pytest.mark.anyio
async def test_search_filings_registers_passages_and_neighbors(make_passage) -> None:
    ctx = make_ctx()
    neighbor = make_passage(chunk_index=6)
    passage = make_passage(neighbors=[neighbor])
    ctx.deps.retriever.search.return_value = [passage]

    result = await search_filings(ctx, "receita por segmento", ticker="VALE3", fiscal_years=[2023])

    assert ctx.deps.registry.passages_by_chunk_id.keys() == {passage.chunk_id, neighbor.chunk_id}
    assert "VALE3 DFP FY2023" in result
    assert str(passage.chunk_id) in result
    ctx.deps.retriever.search.assert_awaited_once_with(
        "receita por segmento", filters=SearchFilters(ticker="VALE3", fiscal_years=[2023])
    )


@pytest.mark.anyio
async def test_search_filings_with_no_hits_says_so() -> None:
    ctx = make_ctx()
    ctx.deps.retriever.search.return_value = []

    result = await search_filings(ctx, "algo inexistente")

    assert result == "No matching passages found in the filing corpus."
    assert not ctx.deps.registry.passages_by_chunk_id


@pytest.mark.anyio
async def test_read_chunks_registers_found_passages(make_passage) -> None:
    ctx = make_ctx()
    first, second = make_passage(), make_passage()
    ctx.deps.retriever.read_chunks.return_value = [first, second]

    result = await read_chunks(ctx, [str(first.chunk_id), str(second.chunk_id)])

    assert ctx.deps.registry.passages_by_chunk_id.keys() == {first.chunk_id, second.chunk_id}
    assert str(second.chunk_id) in result
    ctx.deps.retriever.read_chunks.assert_awaited_once_with([first.chunk_id, second.chunk_id])


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("chunk_ids", "error"),
    [
        (["not-a-uuid"], "invalid chunk_id"),
        ([], "at least one id"),
        ([str(uuid4()) for _ in range(11)], "at most 10"),
    ],
)
async def test_read_chunks_rejects_bad_input_without_querying(chunk_ids, error) -> None:
    ctx = make_ctx()

    result = await read_chunks(ctx, chunk_ids)

    assert result.startswith("Error:") and error in result
    ctx.deps.retriever.read_chunks.assert_not_awaited()


@pytest.mark.anyio
async def test_read_chunks_reports_not_found() -> None:
    ctx = make_ctx()
    ctx.deps.retriever.read_chunks.return_value = []

    result = await read_chunks(ctx, [str(uuid4())])

    assert result.startswith("Error:")
    assert not ctx.deps.registry.passages_by_chunk_id


@pytest.mark.anyio
async def test_read_surrounding_chunks_registers_anchor_and_neighbors(make_passage) -> None:
    ctx = make_ctx()
    before, anchor, after = make_passage(chunk_index=6), make_passage(chunk_index=7), make_passage(chunk_index=8)
    ctx.deps.retriever.read_surrounding.return_value = [before, anchor, after]

    await read_surrounding_chunks(ctx, str(anchor.chunk_id), radius=1)

    assert len(ctx.deps.registry.passages_by_chunk_id) == 3
    ctx.deps.retriever.read_surrounding.assert_awaited_once_with(anchor.chunk_id, 1)


@pytest.mark.anyio
@pytest.mark.parametrize(("chunk_id", "radius"), [(str(uuid4()), 0), (str(uuid4()), 4), ("not-a-uuid", 1)])
async def test_read_surrounding_chunks_rejects_bad_input_without_querying(chunk_id, radius) -> None:
    ctx = make_ctx()

    result = await read_surrounding_chunks(ctx, chunk_id, radius=radius)

    assert result.startswith("Error:")
    ctx.deps.retriever.read_surrounding.assert_not_awaited()


@pytest.mark.anyio
async def test_search_filings_stops_after_the_per_turn_budget(make_passage) -> None:
    ctx = make_ctx()
    ctx.deps.retriever.search.return_value = [make_passage()]

    for _ in range(MAX_SEARCHES_PER_TURN):
        assert not (await search_filings(ctx, "receita")).startswith("Error:")
    result = await search_filings(ctx, "receita")

    assert result.startswith("Error: search limit reached")
    assert ctx.deps.retriever.search.await_count == MAX_SEARCHES_PER_TURN


@pytest.mark.anyio
async def test_read_chunks_returns_full_text_beyond_search_excerpt_cap(make_passage) -> None:
    ctx = make_ctx()
    long_table_tail = "| Receita líquida total | 208.066 |"
    passage = make_passage(content="x " * 1000 + long_table_tail)
    ctx.deps.retriever.read_chunks.return_value = [passage]

    result = await read_chunks(ctx, [str(passage.chunk_id)])

    assert long_table_tail in result
