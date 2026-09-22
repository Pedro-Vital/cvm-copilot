"""Chat thread CRUD and the streaming turn endpoint."""

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, status
from fastapi.responses import StreamingResponse

from app.auth.dependencies import CurrentUser, get_current_user
from app.chat.messages import CamelModel, UIMessage
from app.chat.orchestrator import run_chat_turn
from app.chat.streaming import SSE_HEADERS
from app.database.chats import (
    create_thread,
    get_thread_or_403_404,
    list_messages,
    list_threads,
)
from app.database.profiles import ensure_profile
from app.database.supabase import get_service_client, get_user_client

router = APIRouter(prefix="/chat", tags=["chat"])


class ChatStreamRequest(CamelModel):
    thread_id: str
    messages: list[UIMessage]


class ThreadCreate(CamelModel):
    title: str | None = None


class ThreadOut(CamelModel):
    id: str
    title: str | None
    created_at: datetime
    updated_at: datetime


class ThreadDetailOut(CamelModel):
    id: str
    title: str | None
    created_at: datetime
    updated_at: datetime
    messages: list[dict]


@router.get("/threads")
async def list_threads_route(current_user: Annotated[CurrentUser, Depends(get_current_user)]) -> list[ThreadOut]:
    client = await get_user_client(current_user.access_token)
    rows = await list_threads(client)
    return [ThreadOut(**row) for row in rows]


@router.post("/threads", status_code=status.HTTP_201_CREATED)
async def create_thread_route(
    body: ThreadCreate,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
) -> ThreadOut:
    # chat_threads.user_id FKs to profiles.id, and profiles has no self-service
    # INSERT policy, so the backend must ensure the row exists first.
    service_client = await get_service_client()
    await ensure_profile(service_client, current_user.id, current_user.email)

    client = await get_user_client(current_user.access_token)
    row = await create_thread(client, current_user.id, body.title)
    return ThreadOut(**row)


@router.get("/threads/{thread_id}")
async def get_thread_route(
    thread_id: str,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
) -> ThreadDetailOut:
    service_client = await get_service_client()
    thread = await get_thread_or_403_404(service_client, thread_id, current_user.id)

    user_client = await get_user_client(current_user.access_token)
    rows = await list_messages(user_client, thread_id)

    return ThreadDetailOut(**thread, messages=[row["message_json"] for row in rows])


@router.post("/stream")
async def stream_route(
    body: ChatStreamRequest,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
) -> StreamingResponse:
    service_client = await get_service_client()
    await get_thread_or_403_404(service_client, body.thread_id, current_user.id)

    user_client = await get_user_client(current_user.access_token)
    generator = run_chat_turn(body.thread_id, body.messages, user_client)
    return StreamingResponse(generator, media_type="text/event-stream", headers=SSE_HEADERS)
