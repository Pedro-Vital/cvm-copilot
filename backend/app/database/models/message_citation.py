import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from .base import Base

if TYPE_CHECKING:
    from .chat_message import ChatMessage
    from .document_chunk import DocumentChunk


class MessageCitation(Base):
    """A citation linking an assistant message to a retrieved source chunk."""

    __tablename__ = "message_citations"
    __table_args__ = (
        UniqueConstraint("message_id", "citation_index", name="uq_message_citations_message_id_citation_index"),
    )

    id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    message_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("chat_messages.id", ondelete="CASCADE"), index=True)
    chunk_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("document_chunks.id", ondelete="CASCADE"), index=True)
    # The [n] marker in the answer text, and the verbatim quote the grounding
    # validator checked against the chunk.
    citation_index: Mapped[int]
    excerpt: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    message: Mapped["ChatMessage"] = relationship(back_populates="citations")
    chunk: Mapped["DocumentChunk"] = relationship(back_populates="citations")
