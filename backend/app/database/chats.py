"""Chat thread and message persistence via the Supabase client."""

from datetime import UTC, datetime
from uuid import uuid4

from fastapi import HTTPException, status
from supabase import AsyncClient

from app.assistant.outputs import Citation

THREADS_TABLE = "chat_threads"
MESSAGES_TABLE = "chat_messages"
CITATIONS_TABLE = "message_citations"


async def list_threads(client: AsyncClient) -> list[dict]:
    response = await client.table(THREADS_TABLE).select("*").order("updated_at", desc=True).execute()
    return response.data


async def create_thread(client: AsyncClient, user_id: str, title: str | None) -> dict:
    # chat_threads.id has a client-side (SQLAlchemy) default only, no Postgres
    # server_default, so it must be generated here — the Supabase REST client
    # bypasses SQLAlchemy entirely.
    row = {"id": str(uuid4()), "user_id": user_id, "title": title}
    response = await client.table(THREADS_TABLE).insert(row).execute()
    return response.data[0]


async def get_thread_or_403_404(service_client: AsyncClient, thread_id: str, user_id: str) -> dict:
    # maybe_single().execute() returns None (not a response object) on zero rows.
    response = await service_client.table(THREADS_TABLE).select("*").eq("id", thread_id).maybe_single().execute()
    thread = response.data if response is not None else None

    if thread is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Thread not found")
    if thread["user_id"] != user_id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not your thread")

    return thread


async def delete_thread(client: AsyncClient, thread_id: str) -> None:
    # Messages and their citations go with it via ON DELETE CASCADE.
    await client.table(THREADS_TABLE).delete().eq("id", thread_id).execute()


async def list_messages(client: AsyncClient, thread_id: str) -> list[dict]:
    response = (
        await client.table(MESSAGES_TABLE).select("*").eq("thread_id", thread_id).order("created_at").execute()
    )
    return response.data


async def insert_message(client: AsyncClient, thread_id: str, role: str, content: str, message_json: dict) -> dict:
    # Same client-side-only id default as chat_threads — see create_thread.
    row = {
        "id": str(uuid4()),
        "thread_id": thread_id,
        "role": role,
        "content": content,
        "message_json": message_json,
    }
    response = await client.table(MESSAGES_TABLE).insert(row).execute()
    return response.data[0]


async def touch_thread(client: AsyncClient, thread_id: str, title: str | None = None) -> None:
    changes = {"updated_at": datetime.now(UTC).isoformat()}
    if title is not None:
        changes["title"] = title
    await client.table(THREADS_TABLE).update(changes).eq("id", thread_id).execute()


async def insert_citations(client: AsyncClient, message_id: str, citations: list[Citation]) -> None:
    if not citations:
        return
    # Same client-side-only id default as chat_threads — see create_thread.
    rows = [
        {
            "id": str(uuid4()),
            "message_id": message_id,
            "chunk_id": str(citation.chunk_id),
            "citation_index": citation.citation_index,
            "excerpt": citation.excerpt,
        }
        for citation in citations
    ]
    await client.table(CITATIONS_TABLE).insert(rows).execute()
