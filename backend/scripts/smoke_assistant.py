"""Run client-brief questions through the real agent (live OpenAI + Supabase).

Prints each answer with its citations, tool calls, usage, and timing. An
answer only prints if it passed grounding validation; otherwise the run
reports that it failed closed.

Run from backend/:
    uv run python -m scripts.smoke_assistant            # all questions
    uv run python -m scripts.smoke_assistant 1 10 vaga  # a subset, by key
"""

import asyncio
import sys
import time

from openai import AsyncOpenAI
from pydantic_ai import Agent, UsageLimits
from pydantic_ai.exceptions import UnexpectedModelBehavior, UsageLimitExceeded
from pydantic_ai.messages import ToolCallPart

from app.assistant.agent import build_agent, build_model
from app.assistant.deps import DocumentAgentDeps, TurnRegistry
from app.config import settings
from app.database.session import create_engine, create_session_factory
from app.logging_setup import configure_logging
from app.retrieval.retriever import DocumentRetriever

# Keys 1–10 are the example questions from docs/client-brief.md. "vaga" is
# outside what a DFP contains and should come back as insufficient evidence.
QUESTIONS = {
    "1": "Como evoluiu a receita líquida da Vale por segmento (minério de ferro, níquel, cobre etc.) entre 2021 e 2025, segundo as notas explicativas das DFPs?",
    "2": "Para a Suzano, como se compararam a margem EBITDA e o lucro líquido entre 2021 e 2025, e quais fatores as notas explicativas apontam como principais responsáveis pelas variações (ex.: preço da celulose, câmbio)?",
    "3": "Como evoluíram a carteira de crédito e a inadimplência (PDD) do Itaú Unibanco entre 2021 e 2025, conforme divulgado nas notas explicativas das DFPs?",
    "4": "Quais foram os principais itens de despesas operacionais da WEG entre 2021 e 2025, e como cresceram em relação à receita líquida no mesmo período?",
    "5": "Compare o CAPEX e os investimentos divulgados nas demonstrações de fluxo de caixa da Vale e da Suzano entre 2021 e 2025 — o que isso sugere sobre o ritmo de investimento de cada uma (expansão em minério vs. capacidade de celulose)?",
    "6": "Para a Magazine Luiza, como evoluíram o patrimônio líquido e os dividendos/JCP distribuídos, segundo a DMPL, entre 2021 e 2025?",
    "7": "Quais contingências e provisões (cíveis, tributárias, trabalhistas) a Suzano divulgou em suas notas explicativas entre 2021 e 2025, e como o valor total provisionado mudou?",
    "8": "Para a Vale, como as notas explicativas descreveram operações com partes relacionadas e instrumentos financeiros derivativos entre 2021 e 2025?",
    "9": "Para cada uma das cinco empresas, resuma a composição do resultado financeiro (receitas e despesas financeiras) na DRE mais recente e identifique mudanças relevantes em relação ao exercício anterior.",
    "10": "As DFPs comprovam que a WEG melhorou sua eficiência operacional entre 2021 e 2025?",
    "vaga": "Qual era a participação de mercado da Magazine Luiza no e-commerce brasileiro em 2024?",
}


async def ask(agent, retriever: DocumentRetriever, key: str, question: str) -> None:
    print("\n" + "=" * 100)
    print(f"[{key}] {question}\n", flush=True)
    deps = DocumentAgentDeps(retriever=retriever, registry=TurnRegistry(), user_id="smoke", thread_id="smoke")
    started = time.perf_counter()
    try:
        async with agent.iter(
            question, deps=deps, usage_limits=UsageLimits(request_limit=settings.agent_request_limit)
        ) as run:
            async for node in run:
                if Agent.is_call_tools_node(node):
                    for part in node.model_response.parts:
                        if isinstance(part, ToolCallPart):
                            print(f"  → {part.tool_name}({part.args_as_dict()})", flush=True)
    except (UnexpectedModelBehavior, UsageLimitExceeded) as exc:
        print(f"\nFAILED CLOSED after {time.perf_counter() - started:.1f}s: {exc}")
        return

    answer = run.result.output
    usage = run.result.usage
    print(f"\n{answer.answer}\n")
    for citation in answer.citations:
        passage = deps.registry.passages_by_chunk_id[citation.chunk_id]
        where = f"{passage.ticker} DFP {passage.fiscal_year} p.{passage.page} ({passage.section})"
        print(f"  [{citation.citation_index}] {where}\n      “{citation.excerpt[:200]}”")
    print(
        f"\ninsufficient_evidence={answer.insufficient_evidence} citations={len(answer.citations)} "
        f"requests={usage.requests} tool_calls={usage.tool_calls} "
        f"tokens={usage.input_tokens}+{usage.output_tokens} time={time.perf_counter() - started:.1f}s"
    )


async def main(keys: list[str]) -> None:
    configure_logging()
    engine = create_engine()
    openai_client = AsyncOpenAI(api_key=settings.openai_api_key)
    retriever = DocumentRetriever(create_session_factory(engine), openai_client)
    agent = build_agent(build_model(openai_client))
    try:
        for key in keys:
            await ask(agent, retriever, key, QUESTIONS[key])
    finally:
        await openai_client.close()
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main(sys.argv[1:] or list(QUESTIONS)))
