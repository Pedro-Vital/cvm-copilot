import json

import pytest

from app.chat.streaming import STREAM_DONE, stream_text_reply


@pytest.mark.anyio
async def test_stream_text_reply_emits_expected_part_sequence() -> None:
    chunks = [chunk async for chunk in stream_text_reply("msg1", "oi tudo bem")]

    assert chunks[0] == 'data: {"type": "start", "messageId": "msg1"}\n\n'
    assert chunks[1] == 'data: {"type": "text-start", "id": "msg1"}\n\n'
    assert chunks[-3] == 'data: {"type": "text-end", "id": "msg1"}\n\n'
    assert chunks[-2] == 'data: {"type": "finish"}\n\n'
    assert chunks[-1] == STREAM_DONE

    deltas = [json.loads(chunk[len("data: ") : -2])["delta"] for chunk in chunks[2:-3]]
    assert "".join(deltas) == "oi tudo bem"
