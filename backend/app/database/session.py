"""Async SQLAlchemy engine for direct Postgres queries (hybrid retrieval).

Retrieval needs raw SQL — pgvector's `<=>` ordering, `ts_rank_cd`, dynamic
metadata filters — that the Supabase REST client can't express. This
connection bypasses RLS, which is acceptable only for read-only corpus
queries: the `source_documents` / `document_chunks` policies already grant
SELECT to every authenticated user, and retrieval only runs after
`get_current_user`. Never use it for per-user data (chats, citations) —
those go through the user-scoped Supabase client.
"""

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.config import settings


def create_engine() -> AsyncEngine:
    return create_async_engine(settings.database_url, pool_pre_ping=True)


def create_session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(engine, expire_on_commit=False)
