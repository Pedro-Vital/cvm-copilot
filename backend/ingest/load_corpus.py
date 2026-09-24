"""One-off loader: reads data/markdown/manifest.json, chunks each filing's
DoclingDocument (`<file>.docling.json`, via ingest/chunking.py's heading-aware
chunker — not Docling's own HybridChunker, see that module's docstring for
why) and generates embeddings, then writes source_documents + document_chunks
rows to Supabase via the service-role client (there's no self-service INSERT
policy on either table — see the initial migration). The Markdown export is
stored on source_documents.markdown_content for reference but isn't what
gets chunked.

Idempotent per filing, keyed on (ticker, fiscal_year, form) — matching
source_documents' unique constraint. A filing with zero chunks is treated as
an incomplete prior run (the source_documents row is inserted before its
chunks, so a crash mid-embedding can leave one without the other) and is
deleted and redone rather than skipped.

Run from the backend project:
    uv run --project backend -m ingest.load_corpus
"""

import asyncio
import json
import logging
from pathlib import Path
from uuid import uuid4

from docling_core.types.doc import DoclingDocument
from openai import AsyncOpenAI
from supabase import AsyncClient

from app.config import settings
from app.database.supabase import get_service_client
from app.retrieval.embeddings import embed_texts
from ingest.chunking import chunk_document

MARKDOWN_DIR = Path(__file__).parent.parent.parent / "data" / "markdown"
CHUNK_INSERT_BATCH_SIZE = 200

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)


def load_manifest() -> dict:
    return json.loads((MARKDOWN_DIR / "manifest.json").read_text(encoding="utf-8"))


async def find_existing_document(client: AsyncClient, ticker: str, fiscal_year: int, form: str) -> dict | None:
    response = (
        await client.table("source_documents")
        .select("id")
        .eq("ticker", ticker)
        .eq("fiscal_year", fiscal_year)
        .eq("form", form)
        .maybe_single()
        .execute()
    )
    return response.data if response is not None else None


async def count_chunks(client: AsyncClient, document_id: str) -> int:
    response = (
        await client.table("document_chunks").select("id", count="exact").eq("document_id", document_id).execute()
    )
    return response.count or 0


def docling_json_path(local_path: str) -> Path:
    return MARKDOWN_DIR / Path(local_path).with_suffix(".docling.json")


async def ingest_filing(client: AsyncClient, openai_client: AsyncOpenAI, filing: dict) -> int:
    markdown_path = (MARKDOWN_DIR / filing["local_path"]).with_suffix(".md")
    markdown_content = markdown_path.read_text(encoding="utf-8")
    document = DoclingDocument.load_from_json(docling_json_path(filing["local_path"]))

    document_id = str(uuid4())
    document_row = {
        "id": document_id,
        "ticker": filing["ticker"],
        "cnpj": filing["cnpj"],
        "company_name": filing["company_name"],
        "codigo_cvm": filing["codigo_cvm"],
        "form": filing["form"],
        "reference_period": filing["reference_period"],
        "fiscal_year": filing["fiscal_year"],
        "source_url": filing["source_url"],
        "markdown_content": markdown_content,
    }
    await client.table("source_documents").insert(document_row).execute()

    chunks = chunk_document(document)
    embeddings = await embed_texts(openai_client, [chunk.content for chunk in chunks])

    # Denormalized onto every chunk (not just source_documents) so a citation
    # can be rendered -- company, filing type, date -- straight from a single
    # document_chunks row, without a join back to source_documents.
    chunk_metadata = {
        "ticker": filing["ticker"],
        "company_name": filing["company_name"],
        "form": filing["form"],
        "fiscal_year": filing["fiscal_year"],
        "reference_period": filing["reference_period"],
    }

    chunk_rows = [
        {
            "id": str(uuid4()),
            "document_id": document_id,
            "chunk_index": chunk.chunk_index,
            "page": chunk.page,
            "section": chunk.section,
            "content": chunk.content,
            "token_count": chunk.token_count,
            "embedding": embedding,
            "metadata": chunk_metadata,
        }
        for chunk, embedding in zip(chunks, embeddings, strict=True)
    ]

    for start in range(0, len(chunk_rows), CHUNK_INSERT_BATCH_SIZE):
        batch = chunk_rows[start : start + CHUNK_INSERT_BATCH_SIZE]
        await client.table("document_chunks").insert(batch).execute()

    return len(chunk_rows)


async def main() -> None:
    manifest = load_manifest()
    client = await get_service_client()
    openai_client = AsyncOpenAI(api_key=settings.openai_api_key)

    for index, filing in enumerate(manifest["filings"], start=1):
        label = f"{filing['ticker']} {filing['fiscal_year']}"
        existing = await find_existing_document(client, filing["ticker"], filing["fiscal_year"], filing["form"])

        if existing:
            chunk_count = await count_chunks(client, existing["id"])
            if chunk_count > 0:
                logger.info("[%d/%d] Skipping %s (already ingested, %d chunks)", index, len(manifest["filings"]), label, chunk_count)
                continue
            logger.warning("[%d/%d] %s has an incomplete prior ingest, redoing", index, len(manifest["filings"]), label)
            await client.table("source_documents").delete().eq("id", existing["id"]).execute()

        chunk_count = await ingest_filing(client, openai_client, filing)
        logger.info("[%d/%d] Ingested %s: %d chunks", index, len(manifest["filings"]), label, chunk_count)


if __name__ == "__main__":
    asyncio.run(main())
