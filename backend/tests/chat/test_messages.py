from app.chat.messages import (
    UIMessage,
    UIMessagePart,
    build_assistant_message,
    extract_text,
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
