"""Shared declarative base and the Supabase-managed `auth.users` stub.

Alembic autogenerate reads `Base.metadata`. Postgres-specific features that
autogenerate can't infer reliably (the `vector` extension, the generated
`tsvector` expression, HNSW/GIN indexes, RLS policies) still need explicit,
reviewed operations in the migration itself — see backend/CLAUDE.md.
"""

from sqlalchemy import Column, Table
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import DeclarativeBase

EMBEDDING_DIMENSIONS = 1536


class Base(DeclarativeBase):
    pass


# Supabase-managed table, not owned by our migrations — declared only so
# `ForeignKey("auth.users.id")` can resolve. Alembic must exclude the `auth`
# schema from autogenerate (see alembic/env.py).
auth_users = Table(
    "users",
    Base.metadata,
    Column("id", PGUUID(as_uuid=True), primary_key=True),
    schema="auth",
)
