import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.assistant.agent import build_agent
from app.chat.messages import UIMessage, UIMessagePart
from app.chat.orchestrator import GROUNDING_FAILURE_MESSAGE, run_chat_turn
from app.chat.streaming import STREAM_DONE
from app.config import settings
from tests.support.scripted_model import ScriptedModel, call_tool, final_answer

EXCERPT = "A receita de vendas líquida totalizou R$ 208,1 bilhões"
MODULE = "app.chat.orchestrator"


@pytest.fixture
def passage(make_passage):
    return make_passage(content=f"{EXCERPT} em 2023.")


@pytest.fixture
def retriever(passage):
    return MagicMock(search=AsyncMock(return_value=[passage]))


@pytest.fixture
def db():
    with (
        patch(f"{MODULE}.insert_message", AsyncMock(side_effect=[{"id": "user-row"}, {"id": "assistant-row"}])) as insert,
        patch(f"{MODULE}.insert_citations", AsyncMock()) as citations,
        patch(f"{MODULE}.touch_thread", AsyncMock()) as touch,
    ):
        yield MagicMock(insert_message=insert, insert_citations=citations, touch_thread=touch)


def user_message(text: str, message_id: str = "u1") -> UIMessage:
    return UIMessage(id=message_id, role="user", parts=[UIMessagePart(type="text", text=text)])


async def run_turn(model: ScriptedModel, retriever, messages: list[UIMessage]) -> list:
    events = [
        event
        async for event in run_chat_turn(
            "thread-1", messages, MagicMock(), agent=build_agent(model), retriever=retriever, user_id="user-1"
        )
    ]
    assert events[-1] == STREAM_DONE
    return [json.loads(event.removeprefix("data: ")) for event in events[:-1]]


@pytest.mark.anyio
async def test_grounded_turn_streams_status_text_citations_and_persists(retriever, passage, db) -> None:
    model = ScriptedModel(
        call_tool("search_filings", query="receita líquida", ticker="VALE3"),
        final_answer(
            answer="A receita foi de R$ 208,1 bilhões [1].",
            citations=[{"citation_index": 1, "chunk_id": str(passage.chunk_id), "excerpt": EXCERPT}],
        ),
    )

    parts = await run_turn(model, retriever, [user_message("Qual a receita da Vale?")])

    types = [part["type"] for part in parts]
    assert types[0] == "start"
    assert types[-1] == "finish"
    statuses = [part["data"]["message"] for part in parts if part["type"] == "data-status"]
    assert statuses == [
        "Analisando a pergunta…",
        "Buscando nas DFPs da VALE3: “receita líquida”",
        "Verificando as citações…",
    ]
    assert all(part["transient"] for part in parts if part["type"] == "data-status")
    text = "".join(part["delta"] for part in parts if part["type"] == "text-delta")
    assert text == "A receita foi de R$ 208,1 bilhões [1]."
    [citation] = [part for part in parts if part["type"] == "data-citation"]
    assert citation["data"]["chunkId"] == str(passage.chunk_id)
    assert citation["data"]["ticker"] == "VALE3"
    assert citation["data"]["referencePeriod"] == "2023-12-31"
    assert types.index("data-citation") > types.index("text-end")

    user_call, assistant_call = db.insert_message.await_args_list
    assert user_call.args[2:4] == ("user", "Qual a receita da Vale?")
    assert assistant_call.args[2:4] == ("assistant", "A receita foi de R$ 208,1 bilhões [1].")
    assert [p["type"] for p in assistant_call.args[4]["parts"]] == ["text", "data-citation"]
    message_id, [saved] = db.insert_citations.await_args.args[1:]
    assert message_id == "assistant-row"
    assert (saved.citation_index, saved.chunk_id) == (1, passage.chunk_id)
    db.touch_thread.assert_awaited_once()


@pytest.mark.anyio
async def test_grounding_failure_streams_error_and_persists_nothing(retriever, passage, db) -> None:
    bad_answer = final_answer(
        answer="A receita caiu [1].",
        citations=[{"citation_index": 1, "chunk_id": str(passage.chunk_id), "excerpt": "texto que não está no trecho"}],
    )
    model = ScriptedModel(
        call_tool("search_filings", query="receita"), *[bad_answer] * (settings.agent_output_retries + 1)
    )

    parts = await run_turn(model, retriever, [user_message("Qual a receita da Vale?")])

    assert parts[-1] == {"type": "error", "errorText": GROUNDING_FAILURE_MESSAGE}
    assert not any(part["type"] in {"text-delta", "data-citation"} for part in parts)
    db.insert_message.assert_not_awaited()
    db.insert_citations.assert_not_awaited()


@pytest.mark.anyio
async def test_prior_turns_reach_the_model_as_history(retriever, db) -> None:
    seen_prompts: list[str] = []
    model = ScriptedModel(final_answer(answer="Evidência insuficiente.", insufficient_evidence=True))
    respond = model._respond

    def spy(messages, info):
        seen_prompts.extend(
            part.content for message in messages for part in message.parts if part.part_kind in {"user-prompt", "text"}
        )
        return respond(messages, info)

    model.function = spy
    history = [
        user_message("Qual a receita da Vale em 2023?", "u0"),
        UIMessage(
            id="a0",
            role="assistant",
            parts=[UIMessagePart(type="text", text="R$ 208,1 bilhões [1]."), UIMessagePart(type="data-citation", data={})],
        ),
    ]

    await run_turn(model, retriever, [*history, user_message("E em 2022?")])

    assert seen_prompts == ["Qual a receita da Vale em 2023?", "R$ 208,1 bilhões [1].", "E em 2022?"]
