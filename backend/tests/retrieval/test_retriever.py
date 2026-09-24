from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID

import pytest

from app.retrieval.retriever import DocumentRetriever
from app.retrieval.types import SearchFilters

A = UUID(int=1)
B = UUID(int=2)
C = UUID(int=3)
NEIGHBOR = UUID(int=11)

MODULE = "app.retrieval.retriever"


def make_retriever() -> DocumentRetriever:
    # MagicMock supports `async with`, standing in for async_sessionmaker.
    return DocumentRetriever(session_factory=MagicMock(), openai_client=MagicMock())


@pytest.fixture
def db(make_row):
    """Patch the search + hydration boundary; tests set return values per case."""
    with (
        patch(f"{MODULE}.embed_query", AsyncMock(return_value=[0.1] * 3)) as embed_query,
        patch(f"{MODULE}.semantic_search", AsyncMock()) as semantic_search,
        patch(f"{MODULE}.full_text_search", AsyncMock()) as full_text_search,
        patch(f"{MODULE}.get_chunks_by_ids", AsyncMock()) as get_chunks_by_ids,
        patch(f"{MODULE}.get_neighbor_chunks", AsyncMock(return_value={})) as get_neighbor_chunks,
    ):
        get_chunks_by_ids.side_effect = lambda session, ids: {i: make_row(chunk_id=i) for i in ids}
        yield MagicMock(
            embed_query=embed_query,
            semantic_search=semantic_search,
            full_text_search=full_text_search,
            get_chunks_by_ids=get_chunks_by_ids,
            get_neighbor_chunks=get_neighbor_chunks,
        )


@pytest.mark.anyio
async def test_search_fuses_both_paths_in_rrf_order(db) -> None:
    db.semantic_search.return_value = [A, B]
    db.full_text_search.return_value = [C, B]

    passages = await make_retriever().search("receita por segmento", include_neighbors=False)

    assert [p.chunk_id for p in passages] == [B, A, C]
    assert passages[0].fusion_score > passages[1].fusion_score
    assert passages[0].ticker == "VALE3"


@pytest.mark.anyio
async def test_search_passes_filters_and_candidate_k_to_both_paths(db) -> None:
    db.semantic_search.return_value = [A]
    db.full_text_search.return_value = []
    filters = SearchFilters(ticker="VALE3", fiscal_years=[2023])

    await make_retriever().search("receita por segmento", filters=filters, candidate_k=25)

    for search in (db.semantic_search, db.full_text_search):
        assert search.call_args.kwargs == {"limit": 25, "filters": filters}
    assert db.full_text_search.call_args.args[1] == "receita por segmento"
    assert db.semantic_search.call_args.args[1] == [0.1] * 3


@pytest.mark.anyio
async def test_search_trims_to_top_k_before_hydrating(db) -> None:
    db.semantic_search.return_value = [A, B, C]
    db.full_text_search.return_value = []

    passages = await make_retriever().search("q", top_k=2, include_neighbors=False)

    assert [p.chunk_id for p in passages] == [A, B]
    assert db.get_chunks_by_ids.call_args.args[1] == [A, B]


@pytest.mark.anyio
async def test_shared_neighbor_attaches_only_to_higher_ranked_hit(db, make_row) -> None:
    db.semantic_search.return_value = [A, B]
    db.full_text_search.return_value = []
    neighbor = make_row(chunk_id=NEIGHBOR, chunk_index=8)
    db.get_neighbor_chunks.return_value = {A: [neighbor], B: [neighbor]}

    passages = await make_retriever().search("q")

    assert [n.chunk_id for n in passages[0].neighbors] == [NEIGHBOR]
    assert passages[0].neighbors[0].fusion_score == 0.0
    assert passages[1].neighbors == []


@pytest.mark.anyio
async def test_search_returns_empty_without_hydrating_when_no_hits(db) -> None:
    db.semantic_search.return_value = []
    db.full_text_search.return_value = []

    assert await make_retriever().search("nada") == []
    db.get_chunks_by_ids.assert_not_called()


@pytest.mark.anyio
async def test_read_chunks_preserves_requested_order_and_skips_missing(db, make_row) -> None:
    db.get_chunks_by_ids.side_effect = lambda session, ids: {B: make_row(chunk_id=B), A: make_row(chunk_id=A)}

    passages = await make_retriever().read_chunks([B, C, A])

    assert [p.chunk_id for p in passages] == [B, A]
