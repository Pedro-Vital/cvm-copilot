"""add citation index and excerpt to message_citations

Revision ID: f7c4c24a200a
Revises: 93a44e078fa2
Create Date: 2026-09-24 12:03:58.764418

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'f7c4c24a200a'
down_revision: str | Sequence[str] | None = '93a44e078fa2'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    # No rows exist yet (the chat stream was stubbed until now), so NOT NULL
    # needs no backfill.
    op.add_column("message_citations", sa.Column("citation_index", sa.Integer(), nullable=False))
    op.add_column("message_citations", sa.Column("excerpt", sa.Text(), nullable=False))
    op.create_unique_constraint(
        "uq_message_citations_message_id_citation_index", "message_citations", ["message_id", "citation_index"]
    )

    # The backend writes citations with the analyst's own (RLS-scoped) client,
    # like their messages, so it needs an INSERT policy scoped to messages in
    # threads they own.
    op.execute(
        'CREATE POLICY "insert_own_message_citations" ON message_citations '
        "FOR INSERT WITH CHECK ("
        "  EXISTS ("
        "    SELECT 1 FROM chat_messages"
        "    JOIN chat_threads ON chat_threads.id = chat_messages.thread_id"
        "    WHERE chat_messages.id = message_citations.message_id"
        "    AND chat_threads.user_id = auth.uid()"
        "  )"
        ")"
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.execute('DROP POLICY IF EXISTS "insert_own_message_citations" ON message_citations')
    op.drop_constraint("uq_message_citations_message_id_citation_index", "message_citations", type_="unique")
    op.drop_column("message_citations", "excerpt")
    op.drop_column("message_citations", "citation_index")
