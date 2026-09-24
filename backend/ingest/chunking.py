"""Heading-aware Markdown chunker for CVM DFP filings, enriched with real
page numbers from the source DoclingDocument.

DFP filings share a CVM-standardized top-level structure (visible in the
"Índice" at the top of every converted filing), and Docling flattens every
heading to the same level in both its own document model and its Markdown
export (CVM's DFP PDFs don't encode real heading hierarchy for Docling to
detect — it's all visually "bold text" at one flat level), so structure has
to be recovered from heading *content*, not nesting:

- Repeated running headers are page-break artifacts (the company name,
  "(Reais Mil)", the notes letterhead) that show up verbatim many times and
  carry no chunk-worthy content of their own. This also means Docling's own
  HybridChunker isn't a good fit here on its own: its heading-trail tracking
  has no way to know "(Reais Mil)" is a trivial unit-label, not a section, so
  it produces worse section labels than the heuristic below despite carrying
  correct page numbers -- confirmed by inspecting its raw output on this
  corpus before choosing this approach.
- A small set of known top-level part names ("Notas Explicativas",
  "Relatório da Administração/Comentário do Desempenho", ...) are also
  repeated running headers, but they mark which part of the filing the
  subsequent numbered notes belong to -- worth tracking so a bare heading
  like "6 Aplicações Financeiras" becomes a self-descriptive section label.
- Everything else that isn't a repeated duplicate is a real section boundary
  (a numbered note, a financial-statement heading, an MD&A subsection).

Real page numbers come from a side channel: DoclingDocument's own
SECTION_HEADER items are in the exact same order as the `## ` headings in
its Markdown export (verified empirically -- both are serializations of the
same underlying heading sequence), so the Nth heading's page number is the
Nth SECTION_HEADER item's provenance. Plain Markdown text alone has no page
numbers at all, which is why chunking now reads the DoclingDocument JSON
saved during conversion instead of the Markdown export -- see
data/README.md.
"""

import re
from dataclasses import dataclass

import tiktoken
from docling_core.types.doc import DoclingDocument
from docling_core.types.doc.document import TextItem
from docling_core.types.doc.labels import DocItemLabel

_HEADING_RE = re.compile(r"^## (.+)$", re.MULTILINE)
_IMAGE_PLACEHOLDER_RE = re.compile(r"^<!-- image -->$\n?", re.MULTILINE)

# CVM standardizes DFP structure: these mark which part of the filing
# follows, but aren't content of their own, so they never start a chunk.
KNOWN_PARTS = {
    "Dados da Empresa",
    "DFs Individuais",
    "DFs Consolidadas",
    "Relatório da Administração/Comentário do Desempenho",
    "Notas Explicativas",
    "Proposta de Orçamento de Capital",
    "Pareceres e Declarações",
}

MIN_CHUNK_TOKENS = 200
MAX_CHUNK_TOKENS = 1200
SPLIT_OVERLAP_TOKENS = 100

_encoding = tiktoken.get_encoding("cl100k_base")


def count_tokens(text: str) -> int:
    return len(_encoding.encode(text))


@dataclass
class Chunk:
    section: str | None
    content: str
    chunk_index: int
    token_count: int
    page: int | None


def chunk_document(document: DoclingDocument) -> list[Chunk]:
    markdown = document.export_to_markdown()
    heading_pages = [
        item.prov[0].page_no if item.prov else None
        for item in document.texts
        if item.label == DocItemLabel.SECTION_HEADER and not _is_picture_caption(item)
    ]
    return chunk_markdown(markdown, heading_pages)


def _is_picture_caption(item: TextItem) -> bool:
    # The layout model occasionally mislabels a chart/image caption as
    # SECTION_HEADER. Docling renders those via the picture's own caption
    # path, not as a `## ` line, so they're absent from the Markdown export
    # and must be excluded here too, or the two sequences drift out of
    # alignment (confirmed on ~60% of this corpus's filings).
    return item.parent is not None and item.parent.cref.startswith("#/pictures/")


def chunk_markdown(markdown: str, heading_pages: list[int | None] | None = None) -> list[Chunk]:
    sections = _split_into_sections(markdown, heading_pages or [])
    merged = _merge_small_sections(sections)

    chunks: list[Chunk] = []
    for section, page, content in merged:
        for piece in _split_oversized(content):
            chunks.append(
                Chunk(section=section, content=piece, chunk_index=len(chunks), token_count=count_tokens(piece), page=page)
            )
    return chunks


def _split_into_sections(markdown: str, heading_pages: list[int | None]) -> list[tuple[str | None, int | None, str]]:
    """Split on `## ` headings into (section_label, page, content) triples,
    merging repeated running headers into surrounding content and tracking
    the current top-level part for headings that don't carry their own
    context. `heading_pages[i]` is the page number of the i-th `## ` heading
    -- the caller is responsible for that alignment (see chunk_document).
    """
    matches = list(_HEADING_RE.finditer(markdown))
    heading_texts = [match.group(1).strip() for match in matches]

    if heading_pages and len(heading_pages) != len(heading_texts):
        raise ValueError(
            f"heading_pages length ({len(heading_pages)}) doesn't match the number of "
            f"'## ' headings in markdown ({len(heading_texts)}) -- alignment assumption broke"
        )

    counts: dict[str, int] = {}
    for text in heading_texts:
        counts[text] = counts.get(text, 0) + 1

    def is_repeated(text: str) -> bool:
        # Genuine sections whose table spans a page break usually repeat their
        # heading exactly twice; running letterheads repeat far more (7+ in
        # this corpus). >2 isn't a perfect split (rare 3-page tables exist)
        # but cleanly separates the overwhelming majority of cases.
        return counts[text] > 2

    sections: list[tuple[str | None, int | None, str]] = []
    current_part: str | None = None
    current_label: str | None = None
    current_page: int | None = None
    pending: list[str] = []

    def flush() -> None:
        content = _clean_block("\n".join(pending))
        if content:
            sections.append((current_label, current_page, content))
        pending.clear()

    preamble_end = matches[0].start() if matches else len(markdown)
    preamble = _clean_block(markdown[:preamble_end])
    if preamble:
        sections.append((None, None, preamble))

    for index, heading in enumerate(heading_texts):
        body_start = matches[index].end()
        body_end = matches[index + 1].start() if index + 1 < len(matches) else len(markdown)
        body = markdown[body_start:body_end]
        page = heading_pages[index] if heading_pages else None

        if heading in KNOWN_PARTS:
            flush()
            current_part = heading
            current_label = None
            continue

        if is_repeated(heading):
            pending.append(body)
            continue

        flush()
        current_label = f"{current_part} — {heading}" if current_part else heading
        current_page = page
        pending.append(body)

    flush()
    return sections


def _clean_block(text: str) -> str:
    text = _IMAGE_PLACEHOLDER_RE.sub("", text)
    return text.strip()


def _merge_small_sections(
    sections: list[tuple[str | None, int | None, str]],
) -> list[tuple[str | None, int | None, str]]:
    """Merge consecutive small sections forward until a chunk reaches
    MIN_CHUNK_TOKENS, keeping the most recent (largest-context) label/page."""
    merged: list[tuple[str | None, int | None, str]] = []
    pending_label: str | None = None
    pending_page: int | None = None
    pending_parts: list[str] = []
    pending_tokens = 0

    for label, page, content in sections:
        pending_parts.append(content)
        pending_tokens += count_tokens(content)
        pending_label = label
        pending_page = page

        if pending_tokens >= MIN_CHUNK_TOKENS:
            merged.append((pending_label, pending_page, "\n\n".join(pending_parts)))
            pending_label, pending_page, pending_parts, pending_tokens = None, None, [], 0

    if pending_parts:
        if merged:
            prev_label, prev_page, prev_content = merged[-1]
            merged[-1] = (
                pending_label or prev_label,
                pending_page if pending_page is not None else prev_page,
                prev_content + "\n\n" + "\n\n".join(pending_parts),
            )
        else:
            merged.append((pending_label, pending_page, "\n\n".join(pending_parts)))

    return merged


def _split_oversized(content: str) -> list[str]:
    tokens = _encoding.encode(content)
    if len(tokens) <= MAX_CHUNK_TOKENS:
        return [content]

    pieces = []
    start = 0
    while start < len(tokens):
        end = min(start + MAX_CHUNK_TOKENS, len(tokens))
        pieces.append(_encoding.decode(tokens[start:end]))
        if end == len(tokens):
            break
        start = end - SPLIT_OVERLAP_TOKENS
    return pieces
