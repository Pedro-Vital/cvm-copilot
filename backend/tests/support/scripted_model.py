"""A FunctionModel that plays back a fixed script of model turns.

Runs the real agent (instructions, tools, grounding validator) with a
deterministic "LLM", so tests exercise the grounding contract end to end.
"""

from collections.abc import Callable

from pydantic_ai.messages import (
    ModelMessage,
    ModelResponse,
    RetryPromptPart,
    ToolCallPart,
)
from pydantic_ai.models.function import AgentInfo, FunctionModel

Step = Callable[[AgentInfo], ModelResponse]


def call_tool(name: str, **args) -> Step:
    return lambda info: ModelResponse(parts=[ToolCallPart(name, args)])


def final_answer(**output) -> Step:
    return lambda info: ModelResponse(parts=[ToolCallPart(info.output_tools[0].name, output)])


class ScriptedModel(FunctionModel):
    def __init__(self, *steps: Step) -> None:
        self.steps = list(steps)
        self.retry_prompts: list[str] = []
        super().__init__(self._respond)

    def _respond(self, messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        for part in messages[-1].parts:
            if isinstance(part, RetryPromptPart):
                self.retry_prompts.append(part.model_response())
        return self.steps.pop(0)(info)
