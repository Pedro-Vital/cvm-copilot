"""Coordinates one /chat/stream turn: stream the reply, then persist both sides.

The caller (the route handler) is responsible for the thread ownership check —
it must happen before a StreamingResponse is constructed, since the 200 status
and headers are already sent once this generator starts yielding.
"""

from collections.abc import AsyncIterator
from uuid import uuid4

from fastapi import HTTPException, status
from supabase import AsyncClient

from app.chat.messages import UIMessage, build_assistant_message, extract_text
from app.chat.streaming import stream_text_reply
from app.database.chats import insert_message, touch_thread

STUB_REPLY = (
    "Esta é uma resposta de teste do CVM Copilot. "
    "A geração de respostas com base nos documentos da CVM ainda não foi implementada."
)


async def run_chat_turn(
    thread_id: str,
    messages: list[UIMessage],
    user_client: AsyncClient,
) -> AsyncIterator[str]:
    if not messages or messages[-1].role != "user":
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Expected a trailing user message")

    user_message = messages[-1]
    user_text = extract_text(user_message)
    if not user_text:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Message has no text content")

    assistant_message_id = str(uuid4())

    async for chunk in stream_text_reply(assistant_message_id, STUB_REPLY):
        yield chunk

    await insert_message(user_client, thread_id, "user", user_text, user_message.model_dump(by_alias=True))
    assistant_message = build_assistant_message(assistant_message_id, STUB_REPLY)
    await insert_message(
        user_client, thread_id, "assistant", STUB_REPLY, assistant_message.model_dump(by_alias=True)
    )
    await touch_thread(user_client, thread_id)
