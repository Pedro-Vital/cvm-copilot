"""Chunk + source-document lookups used to hydrate retrieval hits.

Rows carry every column a `RetrievedPassage` needs, so hydration is one
query no matter how many hits or neighbors there are.
"""

from collections import defaultdict
from uuid import UUID

from sqlalchemy import RowMapping, text
from sqlalchemy.ext.asyncio import AsyncSession

PASSAGE_COLUMNS = """
    dc.id AS chunk_id, dc.document_id, dc.chunk_index, dc.content, dc.page, dc.section,
    sd.ticker, sd.company_name, sd.form, sd.fiscal_year, sd.reference_period, sd.source_url
"""


async def get_chunks_by_ids(session: AsyncSession, chunk_ids: list[UUID]) -> dict[UUID, RowMapping]:
    if not chunk_ids:
        return {}
    result = await session.execute(
        text(f"""
            SELECT {PASSAGE_COLUMNS}
            FROM document_chunks dc
            JOIN source_documents sd ON sd.id = dc.document_id
            WHERE dc.id = ANY(:chunk_ids)
        """),
        {"chunk_ids": chunk_ids},
    )
    return {row["chunk_id"]: row for row in result.mappings()}


async def get_neighbor_chunks(
    session: AsyncSession, anchor_ids: list[UUID], radius: int
) -> dict[UUID, list[RowMapping]]:
    """Chunks within `radius` of each anchor in the same document, keyed by anchor id.

    Anchors themselves are excluded, including when one anchor neighbors another.
    """
    if not anchor_ids or radius < 1:
        return {}
    result = await session.execute(
        text(f"""
            SELECT a.id AS anchor_id, {PASSAGE_COLUMNS}
            FROM document_chunks a
            JOIN document_chunks dc
              ON dc.document_id = a.document_id
             AND dc.chunk_index BETWEEN a.chunk_index - :radius AND a.chunk_index + :radius
            JOIN source_documents sd ON sd.id = dc.document_id
            WHERE a.id = ANY(:anchor_ids) AND dc.id <> ALL(:anchor_ids)
            ORDER BY a.id, dc.chunk_index
        """),
        {"anchor_ids": anchor_ids, "radius": radius},
    )
    neighbors: dict[UUID, list[RowMapping]] = defaultdict(list)
    for row in result.mappings():
        neighbors[row["anchor_id"]].append(row)
    return neighbors


async def get_surrounding_chunks(session: AsyncSession, chunk_id: UUID, radius: int) -> list[RowMapping]:
    """The anchor chunk plus up to `radius` chunks on each side, in document order."""
    result = await session.execute(
        text(f"""
            SELECT {PASSAGE_COLUMNS}
            FROM document_chunks a
            JOIN document_chunks dc
              ON dc.document_id = a.document_id
             AND dc.chunk_index BETWEEN a.chunk_index - :radius AND a.chunk_index + :radius
            JOIN source_documents sd ON sd.id = dc.document_id
            WHERE a.id = :chunk_id
            ORDER BY dc.chunk_index
        """),
        {"chunk_id": chunk_id, "radius": radius},
    )
    return list(result.mappings())
