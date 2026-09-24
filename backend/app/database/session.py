"""Async SQLAlchemy engine for direct Postgres queries (hybrid retrieval).

Retrieval needs raw SQL — pgvector's `<=>` ordering, `ts_rank_cd`, dynamic
metadata filters — that the Supabase REST client can't express. This
connection bypasses RLS, which is acceptable only for read-only corpus
queries: the `source_documents` / `document_chunks` policies already grant
SELECT to every authenticated user, and retrieval only runs after
`get_current_user`. Never use it for per-user data (chats, citations) —
those go through the user-scoped Supabase client.
"""

from sqlalchemy import event
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.config import settings

# Supabase is ~200ms away per round trip while the queries themselves run
# in single-digit ms, so round trips are the cost to minimize. Retrieval is
# read-only, so AUTOCOMMIT drops the BEGIN/ROLLBACK round trips around every
# session, and recycling connections replaces a per-checkout pre-ping.
POOL_RECYCLE_SECONDS = 1800


def create_engine() -> AsyncEngine:
    engine = create_async_engine(
        settings.database_url, isolation_level="AUTOCOMMIT", pool_recycle=POOL_RECYCLE_SECONDS
    )
    event.listen(engine.sync_engine, "connect", _configure_hnsw)
    return engine


def _configure_hnsw(dbapi_connection, _connection_record) -> None:
    # HNSW applies WHERE filters *after* the index scan and returns at most
    # `ef_search` candidates, so a ticker filter could leave zero rows.
    # pgvector 0.8 iterative scans keep walking the index until the LIMIT is
    # met; strict_order keeps results exactly distance-ordered. Set once per
    # connection instead of per query to save a round trip on every search.
    cursor = dbapi_connection.cursor()
    cursor.execute("SET hnsw.iterative_scan = strict_order")
    cursor.execute(f"SET hnsw.ef_search = {max(settings.retrieval_candidate_k, 40)}")
    cursor.close()


def create_session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(engine, expire_on_commit=False)
