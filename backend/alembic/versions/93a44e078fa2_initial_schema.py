"""initial schema

Revision ID: 93a44e078fa2
Revises:
Create Date: 2026-09-21 11:34:10.580913

"""

from collections.abc import Sequence

import sqlalchemy as sa
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "93a44e078fa2"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.create_table(
        "source_documents",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("ticker", sa.Text(), nullable=False),
        sa.Column("cnpj", sa.Text(), nullable=False),
        sa.Column("company_name", sa.Text(), nullable=False),
        sa.Column("codigo_cvm", sa.Text(), nullable=False),
        sa.Column("form", sa.Text(), nullable=False),
        sa.Column("reference_period", sa.Date(), nullable=False),
        sa.Column("fiscal_year", sa.Integer(), nullable=False),
        sa.Column("source_url", sa.Text(), nullable=False),
        sa.Column("markdown_content", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("ticker", "fiscal_year", "form", name="uq_source_documents_ticker_year_form"),
    )
    op.create_index(op.f("ix_source_documents_ticker"), "source_documents", ["ticker"], unique=False)

    op.create_table(
        "document_chunks",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("document_id", sa.UUID(), nullable=False),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("page", sa.Integer(), nullable=True),
        sa.Column("section", sa.Text(), nullable=True),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("token_count", sa.Integer(), nullable=True),
        sa.Column("embedding", Vector(1536), nullable=False),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["document_id"], ["source_documents.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_document_chunks_document_id"), "document_chunks", ["document_id"], unique=False)

    # Generated column + indexes: not representable by the SQLAlchemy model,
    # written explicitly and reviewed here per backend/CLAUDE.md.
    op.execute(
        "ALTER TABLE document_chunks "
        "ADD COLUMN search_vector tsvector "
        "GENERATED ALWAYS AS (to_tsvector('portuguese', content)) STORED"
    )
    op.execute("CREATE INDEX ix_document_chunks_search_vector ON document_chunks USING gin (search_vector)")
    op.execute("CREATE INDEX ix_document_chunks_embedding_hnsw ON document_chunks USING hnsw (embedding vector_cosine_ops)")

    op.create_table(
        "profiles",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("email", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["id"], ["auth.users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
    )

    op.create_table(
        "chat_threads",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("title", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["profiles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_chat_threads_user_id"), "chat_threads", ["user_id"], unique=False)

    op.create_table(
        "chat_messages",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("thread_id", sa.UUID(), nullable=False),
        sa.Column("role", sa.Text(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("message_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["thread_id"], ["chat_threads.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_chat_messages_thread_id"), "chat_messages", ["thread_id"], unique=False)

    op.create_table(
        "message_citations",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("message_id", sa.UUID(), nullable=False),
        sa.Column("chunk_id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["chunk_id"], ["document_chunks.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["message_id"], ["chat_messages.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_message_citations_chunk_id"), "message_citations", ["chunk_id"], unique=False)
    op.create_index(op.f("ix_message_citations_message_id"), "message_citations", ["message_id"], unique=False)

    # --- Row-level security ---
    # Chat data is per-analyst. The shared filing corpus (source_documents,
    # document_chunks) is readable by any signed-in analyst; it's only ever
    # written by the backend via the service-role key, which bypasses RLS.

    op.execute("ALTER TABLE profiles ENABLE ROW LEVEL SECURITY")
    op.execute('CREATE POLICY "select_own_profile" ON profiles FOR SELECT USING (auth.uid() = id)')
    op.execute('CREATE POLICY "update_own_profile" ON profiles FOR UPDATE USING (auth.uid() = id)')

    op.execute("ALTER TABLE chat_threads ENABLE ROW LEVEL SECURITY")
    op.execute(
        'CREATE POLICY "manage_own_threads" ON chat_threads '
        "FOR ALL USING (auth.uid() = user_id) WITH CHECK (auth.uid() = user_id)"
    )

    op.execute("ALTER TABLE chat_messages ENABLE ROW LEVEL SECURITY")
    op.execute(
        'CREATE POLICY "manage_own_thread_messages" ON chat_messages '
        "FOR ALL USING ("
        "  EXISTS ("
        "    SELECT 1 FROM chat_threads"
        "    WHERE chat_threads.id = chat_messages.thread_id"
        "    AND chat_threads.user_id = auth.uid()"
        "  )"
        ") "
        "WITH CHECK ("
        "  EXISTS ("
        "    SELECT 1 FROM chat_threads"
        "    WHERE chat_threads.id = chat_messages.thread_id"
        "    AND chat_threads.user_id = auth.uid()"
        "  )"
        ")"
    )

    op.execute("ALTER TABLE message_citations ENABLE ROW LEVEL SECURITY")
    op.execute(
        'CREATE POLICY "select_own_message_citations" ON message_citations '
        "FOR SELECT USING ("
        "  EXISTS ("
        "    SELECT 1 FROM chat_messages"
        "    JOIN chat_threads ON chat_threads.id = chat_messages.thread_id"
        "    WHERE chat_messages.id = message_citations.message_id"
        "    AND chat_threads.user_id = auth.uid()"
        "  )"
        ")"
    )

    op.execute("ALTER TABLE source_documents ENABLE ROW LEVEL SECURITY")
    op.execute(
        'CREATE POLICY "authenticated_read_source_documents" ON source_documents '
        "FOR SELECT USING (auth.role() = 'authenticated')"
    )

    op.execute("ALTER TABLE document_chunks ENABLE ROW LEVEL SECURITY")
    op.execute(
        'CREATE POLICY "authenticated_read_document_chunks" ON document_chunks '
        "FOR SELECT USING (auth.role() = 'authenticated')"
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.execute('DROP POLICY IF EXISTS "authenticated_read_document_chunks" ON document_chunks')
    op.execute("ALTER TABLE document_chunks DISABLE ROW LEVEL SECURITY")

    op.execute('DROP POLICY IF EXISTS "authenticated_read_source_documents" ON source_documents')
    op.execute("ALTER TABLE source_documents DISABLE ROW LEVEL SECURITY")

    op.execute('DROP POLICY IF EXISTS "select_own_message_citations" ON message_citations')
    op.execute("ALTER TABLE message_citations DISABLE ROW LEVEL SECURITY")

    op.execute('DROP POLICY IF EXISTS "manage_own_thread_messages" ON chat_messages')
    op.execute("ALTER TABLE chat_messages DISABLE ROW LEVEL SECURITY")

    op.execute('DROP POLICY IF EXISTS "manage_own_threads" ON chat_threads')
    op.execute("ALTER TABLE chat_threads DISABLE ROW LEVEL SECURITY")

    op.execute('DROP POLICY IF EXISTS "update_own_profile" ON profiles')
    op.execute('DROP POLICY IF EXISTS "select_own_profile" ON profiles')
    op.execute("ALTER TABLE profiles DISABLE ROW LEVEL SECURITY")

    op.drop_index(op.f("ix_message_citations_message_id"), table_name="message_citations")
    op.drop_index(op.f("ix_message_citations_chunk_id"), table_name="message_citations")
    op.drop_table("message_citations")

    op.drop_index(op.f("ix_chat_messages_thread_id"), table_name="chat_messages")
    op.drop_table("chat_messages")

    op.drop_index(op.f("ix_chat_threads_user_id"), table_name="chat_threads")
    op.drop_table("chat_threads")

    op.drop_table("profiles")

    op.execute("DROP INDEX IF EXISTS ix_document_chunks_embedding_hnsw")
    op.execute("DROP INDEX IF EXISTS ix_document_chunks_search_vector")
    op.drop_index(op.f("ix_document_chunks_document_id"), table_name="document_chunks")
    op.drop_table("document_chunks")

    op.drop_index(op.f("ix_source_documents_ticker"), table_name="source_documents")
    op.drop_table("source_documents")
