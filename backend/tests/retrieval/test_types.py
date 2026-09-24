from app.retrieval.types import (
    MAX_AGENT_OUTPUT_CHARS,
    MAX_PASSAGE_EXCERPT_CHARS,
    compact_text,
    format_passages_for_agent,
    normalize_for_match,
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


PADDED_TABLE = (
    "|                    | 2023          | 2022          |\n"
    "|--------------------|---------------|---------------|\n"
    "| Minério de ferro   | 159.425       | 170.186       |"
)


def test_compact_text_squeezes_table_padding_but_keeps_rows() -> None:
    assert compact_text(PADDED_TABLE) == (
        "| | 2023 | 2022 |\n"
        "|---|---|---|\n"
        "| Minério de ferro | 159.425 | 170.186 |"
    )


def test_quote_copied_from_compacted_text_matches_original() -> None:
    quote = compact_text(PADDED_TABLE).splitlines()[2]

    assert normalize_for_match(quote) in normalize_for_match(PADDED_TABLE)
    assert normalize_for_match(compact_text(PADDED_TABLE)) == normalize_for_match(PADDED_TABLE)


def test_full_text_skips_the_excerpt_cap(make_passage) -> None:
    content = "z" * (MAX_PASSAGE_EXCERPT_CHARS + 500)

    output = format_passages_for_agent([make_passage(content=content)], full_text=True)

    assert content in output
