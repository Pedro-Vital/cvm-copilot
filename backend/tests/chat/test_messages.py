from pydantic_ai.messages import ModelRequest, ModelResponse

from app.chat.messages import (
    MAX_HISTORY_MESSAGES,
    UIMessage,
    UIMessagePart,
    build_assistant_message,
    extract_text,
    to_model_history,
)


def test_extract_text_concatenates_text_parts() -> None:
    message = UIMessage(
        id="m1",
        role="user",
        parts=[
            UIMessagePart(type="text", text="Qual foi a "),
            UIMessagePart(type="text", text="receita da Vale?"),
        ],
    )

    assert extract_text(message) == "Qual foi a receita da Vale?"


def test_build_assistant_message_shape() -> None:
    message = build_assistant_message("m2", "olá")

    assert message.id == "m2"
    assert message.role == "assistant"
    assert message.parts == [UIMessagePart(type="text", text="olá")]


def test_incoming_parts_of_any_type_are_accepted_and_preserved() -> None:
    message = UIMessage.model_validate(
        {
            "id": "a1",
            "role": "assistant",
            "parts": [
                {"type": "text", "text": "Receita [1]."},
                {"type": "data-citation", "id": "citation-1", "data": {"chunkId": "c1"}},
            ],
        }
    )

    assert extract_text(message) == "Receita [1]."
    assert message.model_dump(by_alias=True, exclude_none=True)["parts"][1] == {
        "type": "data-citation",
        "id": "citation-1",
        "data": {"chunkId": "c1"},
    }


def test_history_is_capped_starts_with_a_user_turn_and_skips_empty_messages() -> None:
    messages = [
        UIMessage(id=f"m{i}", role="user" if i % 2 == 0 else "assistant", parts=[UIMessagePart(type="text", text=f"t{i}")])
        for i in range(MAX_HISTORY_MESSAGES + 4)
    ]
    messages.append(UIMessage(id="empty", role="assistant", parts=[UIMessagePart(type="data-citation")]))

    history = to_model_history(messages)

    # Window is m5..m13 + the empty message: m5 (an answer) is dropped so
    # history opens with a question, and the empty message is skipped.
    assert len(history) == MAX_HISTORY_MESSAGES - 2
    assert isinstance(history[0], ModelRequest)
    assert history[0].parts[0].content == "t6"
    assert isinstance(history[-1], ModelResponse)
