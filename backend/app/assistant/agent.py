"""PydanticAI document agent: tools over hybrid retrieval, grounded structured output."""

from pathlib import Path

import pydantic_ai
from openai import AsyncOpenAI
from pydantic_ai import Agent, ModelRetry, RunContext
from pydantic_ai.models import Model
from pydantic_ai.models.openai import OpenAIResponsesModel, OpenAIResponsesModelSettings
from pydantic_ai.providers.openai import OpenAIProvider

from app.assistant.deps import DocumentAgentDeps
from app.assistant.outputs import GroundedAnswer
from app.assistant.tools import read_chunks, read_surrounding_chunks, search_filings
from app.config import settings
from app.grounding.validator import validate_grounding

# Otherwise the first run prints an ASCII-art Logfire banner into server logs.
pydantic_ai.BANNER_ENABLED = False

INSTRUCTIONS = (Path(__file__).parent / "instructions.md").read_text(encoding="utf-8")

DocumentAgent = Agent[DocumentAgentDeps, GroundedAnswer]


def build_model(openai_client: AsyncOpenAI) -> Model:
    return OpenAIResponsesModel(
        settings.openai_chat_model,
        provider=OpenAIProvider(openai_client=openai_client),
        settings=OpenAIResponsesModelSettings(openai_reasoning_effort=settings.openai_reasoning_effort),
    )


def build_agent(model: Model) -> DocumentAgent:
    agent = Agent(
        model,
        deps_type=DocumentAgentDeps,
        output_type=GroundedAnswer,
        instructions=INSTRUCTIONS,
        tools=[search_filings, read_chunks, read_surrounding_chunks],
        retries=settings.agent_output_retries,
    )

    @agent.output_validator
    async def enforce_grounding(ctx: RunContext[DocumentAgentDeps], answer: GroundedAnswer) -> GroundedAnswer:
        # Raising ModelRetry sends the errors back to the model to fix; once
        # retries run out the run raises UnexpectedModelBehavior and the
        # orchestrator fails the turn closed.
        errors = validate_grounding(answer, ctx.deps.registry)
        if errors:
            raise ModelRetry("Grounding validation failed:\n" + "\n".join(f"- {error}" for error in errors))
        return answer

    return agent
