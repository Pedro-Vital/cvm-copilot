"""The trust contract: every citation must point at evidence retrieved this turn.

Pure and deterministic — no I/O, no LLM. The agent runs it as an output
validator (errors are fed back to the model to fix), and a turn whose
answer still fails after the allowed retries is never shown or persisted.
"""

import re

from app.assistant.deps import TurnRegistry
from app.assistant.outputs import GroundedAnswer
from app.retrieval.types import normalize_for_match

CITATION_MARKER_RE = re.compile(r"\[(\d+)\]")

# Shorter excerpts ("2023", "R$ 1,2") are substrings of almost any chunk and
# prove nothing about where a claim came from.
MIN_EXCERPT_CHARS = 20


def validate_grounding(answer: GroundedAnswer, registry: TurnRegistry) -> list[str]:
    """Return every contract violation, phrased as instructions the model can act on."""
    if not answer.answer.strip():
        return ["The answer text is empty."]

    if answer.insufficient_evidence:
        if answer.citations:
            return ["When insufficient_evidence is true, citations must be empty."]
        return []

    if not answer.citations:
        return ["Every answer must cite at least one passage, or set insufficient_evidence to true."]

    errors: list[str] = []
    indices = [citation.citation_index for citation in answer.citations]
    if sorted(indices) != list(range(1, len(indices) + 1)):
        errors.append(f"citation_index values must be unique and numbered 1..{len(indices)}; got {sorted(indices)}.")

    markers = {int(number) for number in CITATION_MARKER_RE.findall(answer.answer)}
    if markers != set(indices):
        errors.append(
            f"The [n] markers in the answer {sorted(markers)} must match the citation_index values {sorted(set(indices))}."
        )

    for citation in answer.citations:
        passage = registry.passages_by_chunk_id.get(citation.chunk_id)
        if passage is None:
            errors.append(
                f"Citation [{citation.citation_index}] cites chunk {citation.chunk_id}, "
                "which no tool returned this turn. Cite only chunk ids from tool results."
            )
            continue
        # Tool output truncates long passages with "..."; a quote that keeps
        # the ellipsis is still an exact quote of the text before it.
        excerpt = normalize_for_match(citation.excerpt).removeprefix("...").removesuffix("...").strip()
        if len(excerpt) < MIN_EXCERPT_CHARS:
            errors.append(
                f"Citation [{citation.citation_index}] excerpt is too short; "
                f"quote at least {MIN_EXCERPT_CHARS} characters of the supporting text."
            )
        elif excerpt not in normalize_for_match(passage.content):
            errors.append(
                f"Citation [{citation.citation_index}] excerpt is not an exact quote of chunk {citation.chunk_id}. "
                "Copy it character-for-character from the chunk text (for tables, copy one full row)."
            )
    return errors
