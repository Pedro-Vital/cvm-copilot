import uuid
from datetime import date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from .base import Base

if TYPE_CHECKING:
    from .document_chunk import DocumentChunk


class SourceDocument(Base):
    """A single CVM filing, normalized to Markdown by the ingestion pipeline."""

    __tablename__ = "source_documents"
    __table_args__ = (UniqueConstraint("ticker", "fiscal_year", "form", name="uq_source_documents_ticker_year_form"),)

    id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    ticker: Mapped[str] = mapped_column(Text, index=True)
    cnpj: Mapped[str] = mapped_column(Text)
    company_name: Mapped[str] = mapped_column(Text)
    codigo_cvm: Mapped[str] = mapped_column(Text)
    form: Mapped[str] = mapped_column(Text)
    reference_period: Mapped[date]
    fiscal_year: Mapped[int]
    source_url: Mapped[str] = mapped_column(Text)
    markdown_content: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    chunks: Mapped[list["DocumentChunk"]] = relationship(back_populates="document", cascade="all, delete-orphan")
