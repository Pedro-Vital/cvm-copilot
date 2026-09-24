"""The two ranked search paths over document_chunks: pgvector and full-text.

Each returns chunk ids best-first; scores are discarded because RRF fuses
ranks, not scores (cosine and ts_rank_cd live on incomparable scales).
"""

from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.retrieval.types import SearchFilters

# Must match the generated `search_vector` column in the initial migration.
FTS_CONFIG = "portuguese"


def build_filters(filters: SearchFilters | None) -> tuple[str, dict[str, object]]:
    clauses: list[str] = []
    params: dict[str, object] = {}
    if filters is not None and filters.ticker is not None:
        clauses.append("sd.ticker = :ticker")
        params["ticker"] = filters.ticker
    if filters is not None and filters.fiscal_years:
        clauses.append("sd.fiscal_year = ANY(:fiscal_years)")
        params["fiscal_years"] = filters.fiscal_years
    return "".join(f" AND {clause}" for clause in clauses), params


def build_semantic_search_sql(filter_sql: str) -> str:
    return f"""
        SELECT dc.id
        FROM document_chunks dc
        JOIN source_documents sd ON sd.id = dc.document_id
        WHERE TRUE{filter_sql}
        ORDER BY dc.embedding <=> CAST(:query_vec AS vector)
        LIMIT :limit
    """


def build_full_text_search_sql(filter_sql: str) -> str:
    # plainto_tsquery ANDs every word, so a full question matches almost
    # nothing. Instead let Postgres drop stopwords and stem the question,
    # then OR the lexemes: ts_rank_cd still ranks chunks matching more terms
    # higher, which behaves like BM25. The `::tsquery` cast (vs to_tsquery)
    # keeps the already-stemmed lexemes from being stemmed a second time.
    return f"""
        WITH q AS (
            SELECT (
                SELECT string_agg(quote_literal(lexeme), ' | ')
                FROM unnest(tsvector_to_array(to_tsvector('{FTS_CONFIG}', :query_text))) AS lexeme
            )::tsquery AS query
        )
        SELECT dc.id
        FROM document_chunks dc
        JOIN source_documents sd ON sd.id = dc.document_id
        CROSS JOIN q
        WHERE dc.search_vector @@ q.query{filter_sql}
        ORDER BY ts_rank_cd(dc.search_vector, q.query) DESC
        LIMIT :limit
    """


# Relies on the HNSW iterative-scan settings applied to every connection in
# app.database.session; without them a filtered query can return zero rows.
async def semantic_search(
    session: AsyncSession, query_vec: list[float], *, limit: int, filters: SearchFilters | None = None
) -> list[UUID]:
    filter_sql, params = build_filters(filters)
    result = await session.execute(
        text(build_semantic_search_sql(filter_sql)),
        {"query_vec": str(query_vec), "limit": limit, **params},
    )
    return list(result.scalars())


async def full_text_search(
    session: AsyncSession, query_text: str, *, limit: int, filters: SearchFilters | None = None
) -> list[UUID]:
    filter_sql, params = build_filters(filters)
    result = await session.execute(
        text(build_full_text_search_sql(filter_sql)),
        {"query_text": query_text, "limit": limit, **params},
    )
    return list(result.scalars())
