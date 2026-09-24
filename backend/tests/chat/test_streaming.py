import json

import pytest

from app.chat.streaming import (
    STREAM_DONE,
    error_event,
    finish_events,
    status_event,
    stream_text,
)


def parse(event: str) -> dict:
    assert event.startswith("data: ") and event.endswith("\n\n")
    return json.loads(event[len("data: ") : -2])


@pytest.mark.anyio
async def test_stream_text_reassembles_exactly() -> None:
    text = "A receita líquida da Vale foi de R$ 208,1 bilhões em 2023 [1]."

    events = [parse(event) async for event in stream_text("msg1", text)]

    assert events[0] == {"type": "text-start", "id": "msg1"}
    assert events[-1] == {"type": "text-end", "id": "msg1"}
    assert "".join(event["delta"] for event in events[1:-1]) == text


def test_status_is_transient_data_part() -> None:
    assert parse(status_event("Buscando…")) == {"type": "data-status", "data": {"message": "Buscando…"}, "transient": True}


def test_non_ascii_is_sent_unescaped() -> None:
    assert "Verificação" in error_event("Verificação falhou")


def test_finish_ends_with_done() -> None:
    assert finish_events() == ['data: {"type": "finish"}\n\n', STREAM_DONE]
