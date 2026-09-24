from uuid import uuid4

import pytest

from app.assistant.deps import TurnRegistry
from app.assistant.outputs import Citation, GroundedAnswer
from app.grounding.validator import validate_grounding

TABLE_CHUNK = (
    "| Segmento                 | 2023      | 2022      |\n"
    "|--------------------------|-----------|-----------|\n"
    "| Soluções de Minério de Ferro | 159.425   | 170.186   |"
)
TEXT_CHUNK = "A receita de vendas líquida totalizou R$ 208,1 bilhões em 2023, redução de 7% em relação a 2022."


@pytest.fixture
def registry(make_passage):
    registry = TurnRegistry()
    registry.register_many([make_passage(content=TEXT_CHUNK), make_passage(content=TABLE_CHUNK)])
    return registry


def chunk_ids(registry: TurnRegistry) -> list:
    return list(registry.passages_by_chunk_id)


def answer(text: str, *citations: Citation, insufficient: bool = False) -> GroundedAnswer:
    return GroundedAnswer(answer=text, citations=list(citations), insufficient_evidence=insufficient)


def test_valid_answer_passes(registry) -> None:
    text_id, table_id = chunk_ids(registry)
    grounded = answer(
        "A receita caiu 7% [1], puxada por minério de ferro [2].",
        Citation(citation_index=1, chunk_id=text_id, excerpt="redução de 7% em relação a 2022"),
        Citation(citation_index=2, chunk_id=table_id, excerpt="| Soluções de Minério de Ferro | 159.425 | 170.186 |"),
    )

    assert validate_grounding(grounded, registry) == []


def test_table_excerpt_matches_despite_collapsed_padding(registry) -> None:
    _, table_id = chunk_ids(registry)
    grounded = answer(
        "Minério de ferro [1].",
        Citation(citation_index=1, chunk_id=table_id, excerpt="Soluções de Minério de Ferro | 159.425 | 170.186"),
    )

    assert validate_grounding(grounded, registry) == []


def test_trailing_ellipsis_from_truncated_tool_output_is_tolerated(registry) -> None:
    text_id, _ = chunk_ids(registry)
    grounded = answer(
        "Receita [1].",
        Citation(citation_index=1, chunk_id=text_id, excerpt="A receita de vendas líquida totalizou R$ 208,1..."),
    )

    assert validate_grounding(grounded, registry) == []


def test_paraphrased_excerpt_fails(registry) -> None:
    text_id, _ = chunk_ids(registry)
    grounded = answer(
        "Receita [1].",
        Citation(citation_index=1, chunk_id=text_id, excerpt="a receita líquida caiu 7% frente a 2022"),
    )

    [error] = validate_grounding(grounded, registry)
    assert "not an exact quote" in error


def test_excerpt_too_short_fails(registry) -> None:
    text_id, _ = chunk_ids(registry)
    grounded = answer("Receita [1].", Citation(citation_index=1, chunk_id=text_id, excerpt="2023"))

    [error] = validate_grounding(grounded, registry)
    assert "too short" in error


def test_citing_an_unretrieved_chunk_fails(registry) -> None:
    grounded = answer(
        "Receita [1].", Citation(citation_index=1, chunk_id=uuid4(), excerpt="redução de 7% em relação a 2022")
    )

    [error] = validate_grounding(grounded, registry)
    assert "no tool returned" in error


def test_marker_without_citation_fails(registry) -> None:
    text_id, _ = chunk_ids(registry)
    grounded = answer(
        "Receita caiu [1] e o EBITDA também [2].",
        Citation(citation_index=1, chunk_id=text_id, excerpt="redução de 7% em relação a 2022"),
    )

    [error] = validate_grounding(grounded, registry)
    assert "markers" in error


def test_citation_indices_must_be_contiguous_from_one(registry) -> None:
    text_id, _ = chunk_ids(registry)
    grounded = answer(
        "Receita [2].", Citation(citation_index=2, chunk_id=text_id, excerpt="redução de 7% em relação a 2022")
    )

    assert any("numbered 1..1" in error for error in validate_grounding(grounded, registry))


def test_uncited_answer_fails(registry) -> None:
    [error] = validate_grounding(answer("A receita caiu 7%."), registry)
    assert "at least one passage" in error


def test_insufficient_evidence_without_citations_passes() -> None:
    grounded = answer("Evidência insuficiente: as DFPs não detalham isso.", insufficient=True)

    assert validate_grounding(grounded, TurnRegistry()) == []


def test_insufficient_evidence_with_citations_fails(registry) -> None:
    text_id, _ = chunk_ids(registry)
    grounded = answer(
        "Evidência insuficiente [1].",
        Citation(citation_index=1, chunk_id=text_id, excerpt="redução de 7% em relação a 2022"),
        insufficient=True,
    )

    [error] = validate_grounding(grounded, registry)
    assert "citations must be empty" in error


def test_empty_answer_fails() -> None:
    assert validate_grounding(answer("  ", insufficient=True), TurnRegistry()) == ["The answer text is empty."]


def test_table_row_quoted_from_compacted_tool_output_passes(make_passage) -> None:
    padded = (
        "| Segmento                     | 2023        |\n"
        "|------------------------------|-------------|\n"
        "| Soluções de Minério de Ferro | 159.425     |"
    )
    registry = TurnRegistry()
    passage = make_passage(content=padded)
    registry.register(passage)
    grounded = answer(
        "Minério de ferro [1].",
        Citation(citation_index=1, chunk_id=passage.chunk_id, excerpt="|---|---|\n| Soluções de Minério de Ferro | 159.425 |"),
    )

    assert validate_grounding(grounded, registry) == []
