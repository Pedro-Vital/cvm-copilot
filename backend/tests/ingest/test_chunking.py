import pytest
from docling_core.types.doc import BoundingBox, DoclingDocument
from docling_core.types.doc.common.reference import ProvenanceItem
from docling_core.types.doc.labels import DocItemLabel

from ingest.chunking import (
    MAX_CHUNK_TOKENS,
    MIN_CHUNK_TOKENS,
    SPLIT_OVERLAP_TOKENS,
    _encoding,
    chunk_document,
    chunk_markdown,
    count_tokens,
)


def _prov(page: int) -> ProvenanceItem:
    return ProvenanceItem(page_no=page, bbox=BoundingBox(l=0, t=0, r=1, b=1), charspan=(0, 1))


def test_repeated_running_header_does_not_start_a_new_chunk() -> None:
    markdown = (
        "## Notas Explicativas\n\n"
        "## 6 APLICAÇÕES FINANCEIRAS\n\n"
        + "A companhia possui aplicações financeiras relevantes. " * 20
        + "\n\n## Notas Explicativas\n\n"
        "## 7 CLIENTES\n\n"
        + "O saldo de clientes é composto por diversos itens. " * 20
    )

    chunks = chunk_markdown(markdown)
    sections = [chunk.section for chunk in chunks]

    assert "Notas Explicativas" not in sections
    assert any("6 APLICAÇÕES FINANCEIRAS" in (section or "") for section in sections)
    assert any("7 CLIENTES" in (section or "") for section in sections)


def test_heading_repeated_exactly_twice_keeps_its_own_label() -> None:
    # A table split across one page break repeats its heading exactly twice
    # (unlike a running letterhead, which repeats far more) -- it must stay
    # its own section, not get folded into whichever section preceded it.
    markdown = (
        "## DFs Individuais / Balanço Patrimonial Ativo\n\n"
        + "Ativo total: 1.000. " * 60
        + "\n\n## DFs Individuais / Balanço Patrimonial Passivo\n\n"
        + "Passivo total: 1.000. " * 60
        + "\n\n## DFs Individuais / Balanço Patrimonial Passivo\n\n"
        + "Continuação do passivo. " * 60
    )

    chunks = chunk_markdown(markdown)
    sections = [chunk.section for chunk in chunks]

    assert "DFs Individuais / Balanço Patrimonial Ativo" in sections
    assert sections.count("DFs Individuais / Balanço Patrimonial Passivo") == 2
    ativo_chunk = next(c for c in chunks if c.section == "DFs Individuais / Balanço Patrimonial Ativo")
    assert "Passivo total" not in ativo_chunk.content


def test_known_part_prefixes_bare_numbered_headings() -> None:
    markdown = "## Notas Explicativas\n\n## 6 APLICAÇÕES FINANCEIRAS\n\n" + "Texto relevante sobre finanças. " * 20

    chunks = chunk_markdown(markdown)

    assert chunks[0].section == "Notas Explicativas — 6 APLICAÇÕES FINANCEIRAS"


def test_breadcrumb_heading_is_not_reprefixed() -> None:
    markdown = "## DFs Individuais / Balanço Patrimonial Ativo\n\n" + "Ativo total: 1.000. " * 20

    chunks = chunk_markdown(markdown)

    assert chunks[0].section == "DFs Individuais / Balanço Patrimonial Ativo"


def test_image_placeholders_are_stripped() -> None:
    markdown = "## 1 INFORMAÇÕES SOBRE A COMPANHIA\n\n<!-- image -->\n\n" + "Texto real da nota. " * 20

    chunks = chunk_markdown(markdown)

    assert "<!-- image -->" not in chunks[0].content


def test_small_adjacent_sections_merge_forward() -> None:
    markdown = (
        "## 2.1 Base de consolidação\n\nTexto curto um.\n\n"
        "## 2.2 Combinações de negócios\n\nTexto curto dois.\n\n"
        "## 2.3 Conversão de moeda estrangeira\n\n" + "Texto mais longo sobre conversão de moeda. " * 40
    )

    chunks = chunk_markdown(markdown)

    assert len(chunks) == 1
    assert "Texto curto um" in chunks[0].content
    assert "Texto curto dois" in chunks[0].content
    assert chunks[0].section == "2.3 Conversão de moeda estrangeira"


def test_oversized_section_splits_with_overlap() -> None:
    long_text = "A receita operacional líquida cresceu de forma consistente no período. " * 300
    markdown = f"## 6 RECEITA OPERACIONAL\n\n{long_text}"
    assert count_tokens(long_text) > MAX_CHUNK_TOKENS * 2  # sanity check the fixture is actually oversized

    chunks = chunk_markdown(markdown)

    assert len(chunks) > 1
    assert all(chunk.token_count <= MAX_CHUNK_TOKENS for chunk in chunks)
    assert all(chunk.section == "6 RECEITA OPERACIONAL" for chunk in chunks)

    # consecutive pieces share exactly SPLIT_OVERLAP_TOKENS tokens
    first_tail = _encoding.encode(chunks[0].content)[-SPLIT_OVERLAP_TOKENS:]
    second_head = _encoding.encode(chunks[1].content)[:SPLIT_OVERLAP_TOKENS]
    assert first_tail == second_head


def test_chunk_index_is_sequential() -> None:
    markdown = (
        "## 1 PRIMEIRA NOTA\n\n" + "Texto da primeira nota. " * 40 + "\n\n## 2 SEGUNDA NOTA\n\n" + "Texto da segunda nota. " * 40
    )

    chunks = chunk_markdown(markdown)

    assert [chunk.chunk_index for chunk in chunks] == list(range(len(chunks)))


def test_preamble_before_first_heading_is_kept() -> None:
    # Preamble content is preserved, but since it's small it merges forward
    # into the next real section rather than floating as its own chunk.
    markdown = "Texto introdutório sem heading. " * 40 + "\n\n## 1 PRIMEIRA NOTA\n\n" + "Texto da nota. " * 40

    chunks = chunk_markdown(markdown)

    assert len(chunks) == 1
    assert "Texto introdutório sem heading." in chunks[0].content
    assert chunks[0].section == "1 PRIMEIRA NOTA"


def test_min_and_max_thresholds_are_sane() -> None:
    assert MIN_CHUNK_TOKENS < MAX_CHUNK_TOKENS


def test_page_number_attaches_to_the_heading_that_started_the_section() -> None:
    markdown = (
        "## 1 PRIMEIRA NOTA\n\n" + "Texto da primeira nota. " * 40 + "\n\n## 2 SEGUNDA NOTA\n\n" + "Texto da segunda nota. " * 40
    )

    chunks = chunk_markdown(markdown, heading_pages=[3, 7])

    assert chunks[0].page == 3
    assert chunks[1].page == 7


def test_page_number_survives_small_section_merge() -> None:
    # When small sections merge forward, the resulting chunk should carry
    # the page of whichever heading its (surviving) label came from.
    markdown = "## 2.1 Nota curta\n\nTexto curto.\n\n## 2.2 Nota maior\n\n" + "Texto mais longo aqui. " * 40

    chunks = chunk_markdown(markdown, heading_pages=[5, 6])

    assert len(chunks) == 1
    assert chunks[0].page == 6


def test_mismatched_heading_pages_length_raises() -> None:
    markdown = "## 1 PRIMEIRA NOTA\n\n" + "Texto. " * 40 + "\n\n## 2 SEGUNDA NOTA\n\n" + "Texto. " * 40

    with pytest.raises(ValueError, match="heading_pages length"):
        chunk_markdown(markdown, heading_pages=[1])


def test_page_is_none_without_heading_pages() -> None:
    markdown = "## 1 PRIMEIRA NOTA\n\n" + "Texto da nota. " * 40

    chunks = chunk_markdown(markdown)

    assert chunks[0].page is None


def test_chunk_document_ignores_section_headers_used_as_picture_captions() -> None:
    # The layout model occasionally mislabels a chart/image caption as
    # SECTION_HEADER; Docling renders those via the picture's own caption
    # path rather than a `## ` line, so they must be excluded from
    # heading_pages or its length drifts out of sync with the real headings
    # in the Markdown export (this broke ingestion on ~60% of the real
    # corpus's filings before being caught and fixed).
    document = DoclingDocument(name="test")
    document.add_heading("1 PRIMEIRA NOTA", prov=_prov(1))
    document.add_text(label=DocItemLabel.TEXT, text="Texto da primeira nota. " * 40, prov=_prov(1))
    picture = document.add_picture(prov=_prov(2))
    document.add_text(label=DocItemLabel.SECTION_HEADER, text="Gráfico de Vendas", prov=_prov(2), parent=picture)
    document.add_heading("2 SEGUNDA NOTA", prov=_prov(3))
    document.add_text(label=DocItemLabel.TEXT, text="Texto da segunda nota. " * 40, prov=_prov(3))

    chunks = chunk_document(document)

    assert [chunk.section for chunk in chunks] == ["1 PRIMEIRA NOTA", "2 SEGUNDA NOTA"]
    assert [chunk.page for chunk in chunks] == [1, 3]
