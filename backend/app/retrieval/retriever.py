"""Hybrid retrieval: embed → semantic + full-text in parallel → RRF → hydrate + neighbors."""

import asyncio
from uuid import UUID

from openai import AsyncOpenAI
from sqlalchemy import RowMapping
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.config import settings
from app.database.documents import (
    get_chunks_by_ids,
    get_neighbor_chunks,
    get_surrounding_chunks,
)
from app.retrieval.embeddings import embed_query
from app.retrieval.fusion import reciprocal_rank_fusion
from app.retrieval.queries import full_text_search, semantic_search
from app.retrieval.types import RetrievedPassage, SearchFilters


class DocumentRetriever:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession], openai_client: AsyncOpenAI) -> None:
        self._session_factory = session_factory
        self._openai_client = openai_client

    async def search(
        self,
        query: str,
        *,
        filters: SearchFilters | None = None,
        top_k: int | None = None,
        candidate_k: int | None = None,
        include_neighbors: bool = True,
    ) -> list[RetrievedPassage]:
        top_k = top_k or settings.retrieval_top_k
        candidate_k = candidate_k or settings.retrieval_candidate_k

        # Full-text search doesn't need the embedding, so it runs while the
        # query is being embedded rather than after.
        semantic_ids, fts_ids = await asyncio.gather(
            self._semantic(query, candidate_k, filters),
            self._full_text(query, candidate_k, filters),
        )
        fused = reciprocal_rank_fusion([semantic_ids, fts_ids], k=settings.retrieval_rrf_k)[:top_k]
        if not fused:
            return []

        fused_ids = [chunk_id for chunk_id, _ in fused]
        async with self._session_factory() as session:
            rows_by_id = await get_chunks_by_ids(session, fused_ids)
            neighbors_by_anchor = (
                await get_neighbor_chunks(session, fused_ids, settings.retrieval_neighbor_radius)
                if include_neighbors
                else {}
            )

        # A chunk can neighbor several hits; attach it only to the first
        # (highest-ranked) one so the agent doesn't read it twice.
        seen: set[UUID] = set(fused_ids)
        passages: list[RetrievedPassage] = []
        for chunk_id, score in fused:
            neighbors = []
            for row in neighbors_by_anchor.get(chunk_id, []):
                if row["chunk_id"] not in seen:
                    seen.add(row["chunk_id"])
                    neighbors.append(_passage(row))
            passages.append(_passage(rows_by_id[chunk_id], fusion_score=score, neighbors=neighbors))
        return passages

    async def read_chunks(self, chunk_ids: list[UUID]) -> list[RetrievedPassage]:
        async with self._session_factory() as session:
            rows_by_id = await get_chunks_by_ids(session, chunk_ids)
        return [_passage(rows_by_id[chunk_id]) for chunk_id in chunk_ids if chunk_id in rows_by_id]

    async def read_surrounding(self, chunk_id: UUID, radius: int) -> list[RetrievedPassage]:
        async with self._session_factory() as session:
            rows = await get_surrounding_chunks(session, chunk_id, radius)
        return [_passage(row) for row in rows]

    # Each search path gets its own session: an AsyncSession can't run two
    # statements concurrently.
    async def _semantic(self, query: str, limit: int, filters: SearchFilters | None) -> list[UUID]:
        query_vec = await embed_query(self._openai_client, query)
        async with self._session_factory() as session:
            return await semantic_search(session, query_vec, limit=limit, filters=filters)

    async def _full_text(self, query: str, limit: int, filters: SearchFilters | None) -> list[UUID]:
        async with self._session_factory() as session:
            return await full_text_search(session, query, limit=limit, filters=filters)


def _passage(
    row: RowMapping, *, fusion_score: float = 0.0, neighbors: list[RetrievedPassage] | None = None
) -> RetrievedPassage:
    return RetrievedPassage(
        chunk_id=row["chunk_id"],
        document_id=row["document_id"],
        chunk_index=row["chunk_index"],
        content=row["content"],
        page=row["page"],
        section=row["section"],
        fusion_score=fusion_score,
        ticker=row["ticker"],
        company_name=row["company_name"],
        form=row["form"],
        fiscal_year=row["fiscal_year"],
        reference_period=row["reference_period"],
        source_url=row["source_url"],
        neighbors=neighbors or [],
    )
