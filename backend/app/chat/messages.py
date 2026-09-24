"""AI SDK UI message wire format and pure conversion helpers."""

from typing import Literal

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel
from pydantic_ai.messages import (
    ModelMessage,
    ModelRequest,
    ModelResponse,
    TextPart,
    UserPromptPart,
)

from app.assistant.deps import TurnRegistry
from app.assistant.outputs import GroundedAnswer

# Enough for follow-ups ("e em 2022?") without resending a long thread's
# worth of answers on every turn.
MAX_HISTORY_MESSAGES = 10


class CamelModel(BaseModel):
    """Base for chat DTOs: snake_case attributes, camelCase wire format."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        serialize_by_alias=True,
    )


class UIMessagePart(CamelModel):
    # History echoes back every part type the AI SDK keeps on a message
    # (text, data-citation, step-start, ...); only text is read, the rest is
    # carried through untouched.
    model_config = ConfigDict(extra="allow")

    type: str
    text: str | None = None


class UIMessage(CamelModel):
    id: str
    role: Literal["user", "assistant", "system"]
    parts: list[UIMessagePart]


def extract_text(message: UIMessage) -> str:
    return "".join(part.text or "" for part in message.parts if part.type == "text")


def to_model_history(messages: list[UIMessage]) -> list[ModelMessage]:
    """Prior turns as text-only PydanticAI history.

    Citations aren't carried over: the model must re-retrieve to cite, since
    the grounding allowlist only covers chunks retrieved in the current turn.
    """
    history: list[ModelMessage] = []
    for message in messages[-MAX_HISTORY_MESSAGES:]:
        text = extract_text(message)
        if not text:
            continue
        if message.role == "user":
            history.append(ModelRequest(parts=[UserPromptPart(content=text)]))
        elif message.role == "assistant" and history:
            # Skipped while history is empty: the cap can cut a thread
            # mid-exchange, and history shouldn't open with an answer to a
            # question the model never sees.
            history.append(ModelResponse(parts=[TextPart(content=text)]))
    return history


def citation_parts(answer: GroundedAnswer, registry: TurnRegistry) -> list[UIMessagePart]:
    """`data-citation` parts: everything the UI needs to render a chip and its source passage."""
    parts: list[UIMessagePart] = []
    for citation in sorted(answer.citations, key=lambda c: c.citation_index):
        passage = registry.passages_by_chunk_id[citation.chunk_id]
        parts.append(
            UIMessagePart(
                type="data-citation",
                id=f"citation-{citation.citation_index}",
                data={
                    "citationIndex": citation.citation_index,
                    "chunkId": str(passage.chunk_id),
                    "documentId": str(passage.document_id),
                    "excerpt": citation.excerpt,
                    "ticker": passage.ticker,
                    "companyName": passage.company_name,
                    "form": passage.form,
                    "fiscalYear": passage.fiscal_year,
                    "referencePeriod": passage.reference_period.isoformat(),
                    "page": passage.page,
                    "section": passage.section,
                    "sourceUrl": passage.source_url,
                },
            )
        )
    return parts


def build_assistant_message(message_id: str, text: str, extra_parts: list[UIMessagePart] | None = None) -> UIMessage:
    parts = [UIMessagePart(type="text", text=text), *(extra_parts or [])]
    return UIMessage(id=message_id, role="assistant", parts=parts)
