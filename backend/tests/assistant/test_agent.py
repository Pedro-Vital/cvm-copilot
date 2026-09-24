"""The real agent (instructions, tools, output validator) against a scripted model."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from pydantic_ai.exceptions import UnexpectedModelBehavior

from app.assistant.agent import build_agent
from app.assistant.deps import DocumentAgentDeps, TurnRegistry
from app.config import settings
from app.retrieval.types import SearchFilters
from tests.support.scripted_model import ScriptedModel, call_tool, final_answer

EXCERPT = "A receita de vendas líquida totalizou R$ 208,1 bilhões"


@pytest.fixture
def passage(make_passage):
    return make_passage(content=f"{EXCERPT} em 2023, redução de 7% em relação a 2022.")


@pytest.fixture
def deps(passage) -> DocumentAgentDeps:
    retriever = MagicMock(search=AsyncMock(return_value=[passage]))
    return DocumentAgentDeps(retriever=retriever, registry=TurnRegistry(), user_id="u1", thread_id="t1")


def cited_answer(chunk_id, excerpt: str = EXCERPT):
    return final_answer(
        answer="A receita líquida foi de R$ 208,1 bilhões [1].",
        citations=[{"citation_index": 1, "chunk_id": str(chunk_id), "excerpt": excerpt}],
    )


@pytest.mark.anyio
async def test_search_then_grounded_answer(deps, passage) -> None:
    model = ScriptedModel(
        call_tool("search_filings", query="receita líquida", ticker="VALE3", fiscal_years=[2023]),
        cited_answer(passage.chunk_id),
    )

    result = await build_agent(model).run("Qual a receita da Vale em 2023?", deps=deps)

    assert result.output.citations[0].chunk_id == passage.chunk_id
    assert model.retry_prompts == []
    deps.retriever.search.assert_awaited_once_with(
        "receita líquida", filters=SearchFilters(ticker="VALE3", fiscal_years=[2023])
    )


@pytest.mark.anyio
async def test_invalid_citation_is_sent_back_and_corrected(deps, passage) -> None:
    model = ScriptedModel(
        call_tool("search_filings", query="receita líquida"),
        cited_answer(passage.chunk_id, excerpt="a receita caiu para 208 bilhões"),  # paraphrase, not a quote
        cited_answer(passage.chunk_id),
    )

    result = await build_agent(model).run("Qual a receita da Vale?", deps=deps)

    assert result.output.citations[0].excerpt == EXCERPT
    [retry] = model.retry_prompts
    assert "not an exact quote" in retry


@pytest.mark.anyio
async def test_citing_without_retrieving_fails_closed(deps, passage) -> None:
    # The model never calls a tool, so nothing it cites is in the registry —
    # and it keeps doing so until retries run out.
    attempts = settings.agent_output_retries + 1
    model = ScriptedModel(*[cited_answer(passage.chunk_id) for _ in range(attempts)])

    with pytest.raises(UnexpectedModelBehavior):
        await build_agent(model).run("Qual a receita da Vale?", deps=deps)

    assert len(model.retry_prompts) == settings.agent_output_retries
    assert all("no tool returned" in retry for retry in model.retry_prompts)


@pytest.mark.anyio
async def test_insufficient_evidence_answer_passes(deps) -> None:
    model = ScriptedModel(
        call_tool("search_filings", query="eficiência operacional IA", ticker="WEGE3"),
        final_answer(
            answer="Evidência insuficiente: as DFPs da WEG não atribuem ganhos de eficiência a essa causa.",
            insufficient_evidence=True,
        ),
    )

    result = await build_agent(model).run("A IA melhorou a eficiência da WEG?", deps=deps)

    assert result.output.insufficient_evidence
    assert result.output.citations == []
