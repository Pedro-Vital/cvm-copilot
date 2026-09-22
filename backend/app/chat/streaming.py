"""SSE framing for the AI SDK UI Message Stream protocol.

Wire format verified against ai-sdk.dev docs: each part is a JSON object
framed as `data: <json>\\n\\n`, terminated by a literal `data: [DONE]\\n\\n`.
"""

import asyncio
import json
from collections.abc import AsyncIterator

STREAM_DONE = "data: [DONE]\n\n"

SSE_HEADERS = {
    "x-vercel-ai-ui-message-stream": "v1",
    "Cache-Control": "no-cache",
    "Connection": "keep-alive",
    "X-Accel-Buffering": "no",
}


def format_sse(data: dict) -> str:
    return f"data: {json.dumps(data)}\n\n"


async def stream_text_reply(message_id: str, text: str) -> AsyncIterator[str]:
    yield format_sse({"type": "start", "messageId": message_id})
    yield format_sse({"type": "text-start", "id": message_id})

    words = text.split(" ")
    for index, word in enumerate(words):
        delta = word if index == len(words) - 1 else f"{word} "
        yield format_sse({"type": "text-delta", "id": message_id, "delta": delta})
        await asyncio.sleep(0.05)

    yield format_sse({"type": "text-end", "id": message_id})
    yield format_sse({"type": "finish"})
    yield STREAM_DONE
