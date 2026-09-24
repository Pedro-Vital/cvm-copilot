"""Print top hybrid-retrieval hits for client-brief-style questions.

Run from backend/:
    uv run python -m scripts.smoke_retrieval
"""

import asyncio

from openai import AsyncOpenAI

from app.config import settings
from app.database.session import create_engine, create_session_factory
from app.retrieval.retriever import DocumentRetriever
from app.retrieval.types import SearchFilters, format_passages_for_agent

SMOKE_QUERIES: list[tuple[str, SearchFilters]] = [
    ("receita líquida por segmento minério de ferro níquel cobre", SearchFilters(ticker="VALE3")),
    ("carteira de crédito e provisão para perdas esperadas (PDD)", SearchFilters(ticker="ITUB4")),
    ("provisões para contingências cíveis, tributárias e trabalhistas", SearchFilters(ticker="SUZB3")),
    ("despesas operacionais com vendas, gerais e administrativas", SearchFilters(ticker="WEGE3")),
]


async def main() -> None:
    engine = create_engine()
    openai_client = AsyncOpenAI(api_key=settings.openai_api_key)
    retriever = DocumentRetriever(create_session_factory(engine), openai_client)
    try:
        for query, filters in SMOKE_QUERIES:
            print("\n" + "=" * 80)
            print(f"Query: {query}\nFilters: {filters.model_dump_json(exclude_none=True)}\n")
            passages = await retriever.search(query, filters=filters, top_k=5, include_neighbors=False)
            print(format_passages_for_agent(passages))
    finally:
        await openai_client.close()
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
