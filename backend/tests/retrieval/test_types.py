from app.retrieval.types import (
    MAX_AGENT_OUTPUT_CHARS,
    MAX_PASSAGE_EXCERPT_CHARS,
    format_passages_for_agent,
)


def test_header_carries_citation_metadata(make_passage) -> None:
    passage = make_passage()

    output = format_passages_for_agent([passage])

    assert output.startswith(
        f"VALE3 DFP FY2023 p.91 (Notas Explicativas — Informações por segmento) [{passage.chunk_id}]: "
    )


def test_neighbors_are_indented_under_their_passage(make_passage) -> None:
    neighbor = make_passage(content="contexto anterior", chunk_index=6)
    passage = make_passage(neighbors=[neighbor])

    lines = format_passages_for_agent([passage]).splitlines()

    assert lines[1] == f"  neighbor idx=6 [{neighbor.chunk_id}]: contexto anterior"


def test_long_excerpt_is_capped(make_passage) -> None:
    output = format_passages_for_agent([make_passage(content="x" * (MAX_PASSAGE_EXCERPT_CHARS + 100))])

    assert "x" * MAX_PASSAGE_EXCERPT_CHARS + "..." in output
    assert "x" * (MAX_PASSAGE_EXCERPT_CHARS + 1) not in output


def test_total_output_is_capped(make_passage) -> None:
    passages = [make_passage(content="y" * MAX_PASSAGE_EXCERPT_CHARS) for _ in range(30)]

    output = format_passages_for_agent(passages)

    assert len(output) < MAX_AGENT_OUTPUT_CHARS + 100
    assert output.endswith("... truncated. Narrow the query or read specific chunks.")


def test_empty_passages() -> None:
    assert format_passages_for_agent([]) == "No matching passages found in the filing corpus."
