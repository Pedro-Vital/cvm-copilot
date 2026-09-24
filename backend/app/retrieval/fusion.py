"""Reciprocal Rank Fusion (Cormack et al., SIGIR 2009).

score(chunk) = sum over rankings of 1 / (k + rank). A chunk ranked well by
both retrievers beats one ranked #1 by only one of them.
"""

from collections import defaultdict
from uuid import UUID


def reciprocal_rank_fusion(rankings: list[list[UUID]], *, k: int = 60) -> list[tuple[UUID, float]]:
    scores: dict[UUID, float] = defaultdict(float)
    for ranking in rankings:
        for rank, chunk_id in enumerate(ranking, start=1):
            scores[chunk_id] += 1.0 / (k + rank)
    return sorted(scores.items(), key=lambda item: -item[1])
