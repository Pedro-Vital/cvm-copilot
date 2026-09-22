"""AI SDK UI message wire format and pure conversion helpers."""

from typing import Literal

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class CamelModel(BaseModel):
    """Base for chat DTOs: snake_case attributes, camelCase wire format."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        serialize_by_alias=True,
    )


class UIMessagePart(CamelModel):
    type: Literal["text"]
    text: str


class UIMessage(CamelModel):
    id: str
    role: Literal["user", "assistant", "system"]
    parts: list[UIMessagePart]


def extract_text(message: UIMessage) -> str:
    return "".join(part.text for part in message.parts if part.type == "text")


def build_assistant_message(message_id: str, text: str) -> UIMessage:
    return UIMessage(id=message_id, role="assistant", parts=[UIMessagePart(type="text", text=text)])
