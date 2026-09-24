"""unique document_id chunk_index on document_chunks

Revision ID: cacdef909427
Revises: f7c4c24a200a
Create Date: 2026-09-24 12:17:25.282860

"""
from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'cacdef909427'
down_revision: str | Sequence[str] | None = 'f7c4c24a200a'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    # Neighbor lookups ("chunks i-1..i+1 of this document") could only use the
    # document_id index, so each one scanned every chunk of the filing (~270
    # rows). A composite key makes it a direct range scan, and also encodes
    # the real invariant: chunk_index is unique within a document. It covers
    # document_id-only lookups too, so the single-column index goes.
    op.create_unique_constraint(
        "uq_document_chunks_document_id_chunk_index", "document_chunks", ["document_id", "chunk_index"]
    )
    op.drop_index("ix_document_chunks_document_id", table_name="document_chunks")


def downgrade() -> None:
    """Downgrade schema."""
    op.create_index("ix_document_chunks_document_id", "document_chunks", ["document_id"], unique=False)
    op.drop_constraint("uq_document_chunks_document_id_chunk_index", "document_chunks", type_="unique")
