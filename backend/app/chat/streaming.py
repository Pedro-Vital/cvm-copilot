"""SSE framing for the AI SDK UI Message Stream protocol.

Wire format verified against ai-sdk.dev docs: each part is a JSON object
framed as `data: <json>\\n\\n`, terminated by a literal `data: [DONE]\\n\\n`.
Custom parts use `data-<name>`; `transient` ones reach the client's onData
callback but aren't stored on the message.
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

WORDS_PER_DELTA = 4


def format_sse(data: dict) -> str:
    return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"


def start_event(message_id: str) -> str:
    return format_sse({"type": "start", "messageId": message_id})


def finish_events() -> list[str]:
    return [format_sse({"type": "finish"}), STREAM_DONE]


def status_event(message: str) -> str:
    return format_sse({"type": "data-status", "data": {"message": message}, "transient": True})


def error_event(error_text: str) -> str:
    return format_sse({"type": "error", "errorText": error_text})


def data_part_event(part: dict) -> str:
    return format_sse(part)


async def stream_text(message_id: str, text: str) -> AsyncIterator[str]:
    """Text in a few words per delta.

    The answer is complete (and grounding-validated) before streaming starts,
    so this only paces the reveal; keep it short.
    """
    yield format_sse({"type": "text-start", "id": message_id})
    words = text.split(" ")
    for start in range(0, len(words), WORDS_PER_DELTA):
        delta = " ".join(words[start : start + WORDS_PER_DELTA])
        if start + WORDS_PER_DELTA < len(words):
            delta += " "
        yield format_sse({"type": "text-delta", "id": message_id, "delta": delta})
        await asyncio.sleep(0.02)
    yield format_sse({"type": "text-end", "id": message_id})
