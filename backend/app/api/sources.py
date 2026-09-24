"""Source passages behind citations, for the trust UI's source panel."""

from datetime import date
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status

from app.auth.dependencies import CurrentUser, get_current_user
from app.chat.messages import CamelModel
from app.retrieval.types import compact_text

router = APIRouter(prefix="/sources", tags=["sources"])

MAX_CONTEXT_RADIUS = 3


class SourceChunkOut(CamelModel):
    chunk_id: UUID
    chunk_index: int
    page: int | None
    section: str | None
    content: str
    is_anchor: bool


class SourceContextOut(CamelModel):
    chunk_id: UUID
    ticker: str
    company_name: str
    form: str
    fiscal_year: int
    reference_period: date
    source_url: str
    chunks: list[SourceChunkOut]


# Auth-gated but not ownership-checked: the filing corpus is shared by every
# analyst, so any signed-in user may read any chunk.
@router.get("/{chunk_id}")
async def get_source_context(
    chunk_id: UUID,
    request: Request,
    _: Annotated[CurrentUser, Depends(get_current_user)],
    radius: Annotated[int, Query(ge=0, le=MAX_CONTEXT_RADIUS)] = 1,
) -> SourceContextOut:
    passages = await request.app.state.retriever.read_surrounding(chunk_id, radius)
    anchor = next((passage for passage in passages if passage.chunk_id == chunk_id), None)
    if anchor is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Source passage not found")

    return SourceContextOut(
        chunk_id=anchor.chunk_id,
        ticker=anchor.ticker,
        company_name=anchor.company_name,
        form=anchor.form,
        fiscal_year=anchor.fiscal_year,
        reference_period=anchor.reference_period,
        source_url=anchor.source_url,
        chunks=[
            SourceChunkOut(
                chunk_id=passage.chunk_id,
                chunk_index=passage.chunk_index,
                page=passage.page,
                section=passage.section,
                # Same padding-squeezed text the agent quoted from.
                content=compact_text(passage.content),
                is_anchor=passage.chunk_id == chunk_id,
            )
            for passage in passages
        ],
    )
