"""Live hybrid retrieval against the ingested Supabase corpus."""

import pytest
from openai import AsyncOpenAI

from app.config import settings
from app.database.session import create_engine, create_session_factory
from app.retrieval.retriever import DocumentRetriever
from app.retrieval.types import SearchFilters

pytestmark = [pytest.mark.integration, pytest.mark.anyio]


@pytest.fixture
async def retriever():
    engine = create_engine()
    openai_client = AsyncOpenAI(api_key=settings.openai_api_key)
    yield DocumentRetriever(create_session_factory(engine), openai_client)
    await openai_client.close()
    await engine.dispose()


async def test_ticker_filter_returns_only_that_company(retriever) -> None:
    passages = await retriever.search("receita líquida por segmento", filters=SearchFilters(ticker="VALE3"))

    assert len(passages) == settings.retrieval_top_k
    assert {p.ticker for p in passages} == {"VALE3"}
    assert any("segmento" in p.content.lower() for p in passages)


async def test_year_filter_is_respected(retriever) -> None:
    filters = SearchFilters(ticker="SUZB3", fiscal_years=[2021, 2022])

    passages = await retriever.search("provisões para contingências", filters=filters)

    assert passages
    assert {p.fiscal_year for p in passages} <= {2021, 2022}


async def test_neighbors_come_from_the_same_document(retriever) -> None:
    passages = await retriever.search("carteira de crédito", filters=SearchFilters(ticker="ITUB4"), top_k=3)

    for passage in passages:
        for neighbor in passage.neighbors:
            assert neighbor.document_id == passage.document_id
            assert abs(neighbor.chunk_index - passage.chunk_index) <= settings.retrieval_neighbor_radius
