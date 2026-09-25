"""Coordinates one /chat/stream turn: agent (with grounding) → persist → stream.

The caller (the route handler) is responsible for the thread ownership check —
it must happen before a StreamingResponse is constructed, since the 200 status
and headers are already sent once this generator starts yielding. For the same
reason, failures after that point become an AI SDK `error` event, not an HTTP
error.
"""

import time
from collections.abc import AsyncIterator
from uuid import uuid4

import structlog
from fastapi import HTTPException, status
from pydantic_ai import Agent, UsageLimits
from pydantic_ai.exceptions import UnexpectedModelBehavior, UsageLimitExceeded
from pydantic_ai.messages import ToolCallPart
from sqlalchemy.exc import SQLAlchemyError
from supabase import AsyncClient

from app.assistant.agent import DocumentAgent
from app.assistant.deps import DocumentAgentDeps, TurnRegistry
from app.chat.messages import (
    UIMessage,
    build_assistant_message,
    citation_parts,
    extract_text,
    to_model_history,
)
from app.chat.streaming import (
    STREAM_DONE,
    data_part_event,
    error_event,
    finish_events,
    start_event,
    status_event,
    stream_text,
)
from app.config import settings
from app.database.chats import insert_citations, insert_message, touch_thread
from app.retrieval.retriever import DocumentRetriever

GROUNDING_FAILURE_MESSAGE = (
    "Encontrei trechos relevantes nas DFPs, mas não consegui verificar a resposta contra eles. "
    "Tente uma pergunta mais específica ou divida-a em partes menores."
)
USAGE_LIMIT_MESSAGE = (
    "A pergunta exigiu buscas demais para uma única resposta. "
    "Tente restringir a empresa, o período ou o tema."
)
RETRIEVAL_FAILURE_MESSAGE = "A busca nas DFPs falhou. Tente novamente em instantes."
GENERIC_FAILURE_MESSAGE = "Não foi possível gerar a resposta agora. Tente novamente em instantes."
THREAD_TITLE_MAX_CHARS = 80

logger = structlog.get_logger(__name__)


def thread_title(question: str) -> str:
    title = " ".join(question.split())
    if len(title) <= THREAD_TITLE_MAX_CHARS:
        return title
    return title[:THREAD_TITLE_MAX_CHARS].rsplit(" ", 1)[0] + "…"


def elapsed_ms(started: float) -> int:
    return round((time.perf_counter() - started) * 1000)


def tool_status(part: ToolCallPart) -> str:
    args = part.args_as_dict()
    if part.tool_name == "search_filings":
        scope = " ".join(
            bit
            for bit in (
                f"da {args['ticker']}" if args.get("ticker") else "",
                f"({', '.join(map(str, args['fiscal_years']))})" if args.get("fiscal_years") else "",
            )
            if bit
        )
        return f"Buscando nas DFPs{' ' + scope if scope else ''}: “{args.get('query', '')}”"
    if part.tool_name == "read_chunks":
        return "Lendo trechos completos…"
    if part.tool_name == "read_surrounding_chunks":
        return "Lendo o contexto ao redor do trecho…"
    # The output tool: the model has drafted its answer and grounding runs next.
    return "Verificando as citações…"


async def run_chat_turn(
    thread_id: str,
    messages: list[UIMessage],
    user_client: AsyncClient,
    *,
    agent: DocumentAgent,
    retriever: DocumentRetriever,
    user_id: str,
) -> AsyncIterator[str]:
    if not messages or messages[-1].role != "user":
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Expected a trailing user message")

    user_message = messages[-1]
    user_text = extract_text(user_message)
    if not user_text:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Message has no text content")

    assistant_message_id = str(uuid4())
    started = time.perf_counter()
    # Bound as contextvars so the agent tools' and grounding validator's log
    # lines carry the same turn_id. This generator runs inside the request's own
    # task, so the binding can't leak into other requests.
    structlog.contextvars.bind_contextvars(turn_id=assistant_message_id, thread_id=thread_id, user_id=user_id)
    logger.info("turn_started", question_chars=len(user_text), history_messages=len(messages) - 1)

    yield start_event(assistant_message_id)
    yield status_event("Analisando a pergunta…")

    deps = DocumentAgentDeps(retriever=retriever, registry=TurnRegistry(), user_id=user_id, thread_id=thread_id)
    try:
        async with agent.iter(
            user_text,
            deps=deps,
            message_history=to_model_history(messages[:-1]),
            usage_limits=UsageLimits(request_limit=settings.agent_request_limit),
        ) as run:
            async for node in run:
                if Agent.is_call_tools_node(node):
                    for part in node.model_response.parts:
                        if isinstance(part, ToolCallPart):
                            yield status_event(tool_status(part))
        answer = run.result.output
    # The response is already a 200 stream, so every failure must become an
    # error event — letting it propagate would just cut the stream off.
    except UnexpectedModelBehavior as exc:
        logger.warning("grounding_failed", error=str(exc), duration_ms=elapsed_ms(started))
        yield error_event(GROUNDING_FAILURE_MESSAGE)
        yield STREAM_DONE
        return
    except UsageLimitExceeded as exc:
        logger.warning("agent_usage_limit_exceeded", error=str(exc), duration_ms=elapsed_ms(started))
        yield error_event(USAGE_LIMIT_MESSAGE)
        yield STREAM_DONE
        return
    except SQLAlchemyError:
        logger.exception("retrieval_failed", duration_ms=elapsed_ms(started))
        yield error_event(RETRIEVAL_FAILURE_MESSAGE)
        yield STREAM_DONE
        return
    except Exception:
        logger.exception("agent_run_failed", duration_ms=elapsed_ms(started))
        yield error_event(GENERIC_FAILURE_MESSAGE)
        yield STREAM_DONE
        return

    usage = run.result.usage
    logger.info(
        "agent_run_done",
        requests=usage.requests,
        tool_calls=usage.tool_calls,
        input_tokens=usage.input_tokens,
        output_tokens=usage.output_tokens,
        citations=len(answer.citations),
        insufficient_evidence=answer.insufficient_evidence,
        duration_ms=elapsed_ms(started),
    )

    parts = citation_parts(answer, deps.registry)
    assistant_message = build_assistant_message(assistant_message_id, answer.answer, parts)

    # Persist before revealing the text: the answer is already validated, and
    # a client disconnecting mid-reveal shouldn't lose a paid-for, grounded turn.
    await insert_message(user_client, thread_id, "user", user_text, user_message.model_dump(by_alias=True, exclude_none=True))
    assistant_row = await insert_message(
        user_client, thread_id, "assistant", answer.answer, assistant_message.model_dump(by_alias=True, exclude_none=True)
    )
    await insert_citations(user_client, assistant_row["id"], answer.citations)
    # The first question names the thread; later turns only bump its recency.
    title = thread_title(user_text) if len(messages) == 1 else None
    await touch_thread(user_client, thread_id, title)

    # Text only starts after validation + persistence, so this is how long the
    # analyst watched status lines before seeing any of the answer.
    first_text_ms = elapsed_ms(started)
    async for event in stream_text(assistant_message_id, answer.answer):
        yield event
    for part in parts:
        yield data_part_event(part.model_dump(by_alias=True, exclude_none=True))
    for event in finish_events():
        yield event
    logger.info("turn_done", first_text_ms=first_text_ms, duration_ms=elapsed_ms(started))
