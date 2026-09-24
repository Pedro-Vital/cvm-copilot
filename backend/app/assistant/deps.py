"""Runtime dependencies for the document agent (PydanticAI `deps_type`)."""

from dataclasses import dataclass, field
from uuid import UUID

from app.retrieval.retriever import DocumentRetriever
from app.retrieval.types import RetrievedPassage


@dataclass
class TurnRegistry:
    """Every chunk a tool showed the agent during one turn — the citation allowlist.

    Grounding validation rejects any citation whose chunk isn't registered here,
    so the model can only cite passages it actually retrieved.
    """

    passages_by_chunk_id: dict[UUID, RetrievedPassage] = field(default_factory=dict)

    def register(self, passage: RetrievedPassage) -> None:
        self.passages_by_chunk_id[passage.chunk_id] = passage
        for neighbor in passage.neighbors:
            self.passages_by_chunk_id[neighbor.chunk_id] = neighbor

    def register_many(self, passages: list[RetrievedPassage]) -> None:
        for passage in passages:
            self.register(passage)


@dataclass
class DocumentAgentDeps:
    retriever: DocumentRetriever
    registry: TurnRegistry
    user_id: str
    thread_id: str
    searches_run: int = 0
