"""Structured output of the document agent.

Field descriptions are sent to the model as part of the output schema, so
they are part of the prompt.
"""

from uuid import UUID

from pydantic import BaseModel, Field


class Citation(BaseModel):
    citation_index: int = Field(description="1-based number used as [n] in the answer text")
    chunk_id: UUID = Field(description="Chunk id shown in brackets in the tool results")
    excerpt: str = Field(
        description=(
            "Passage copied character-for-character from that chunk's text that supports the claim. "
            "Do not paraphrase, translate, or clean up table formatting."
        )
    )


class GroundedAnswer(BaseModel):
    answer: str = Field(description="Answer in Portuguese with [n] markers after each factual claim")
    citations: list[Citation] = Field(
        default_factory=list, description="One entry per [n] marker used in the answer"
    )
    insufficient_evidence: bool = Field(
        default=False,
        description="True when the retrieved filings don't support an answer; citations must then be empty",
    )
