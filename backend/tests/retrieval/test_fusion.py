from uuid import UUID

import pytest

from app.retrieval.fusion import reciprocal_rank_fusion

A = UUID(int=1)
B = UUID(int=2)
C = UUID(int=3)


def test_agreement_beats_single_top_rank() -> None:
    # B is #2 in both lists; A is #1 in only one. Agreement wins.
    fused = reciprocal_rank_fusion([[A, B], [C, B]], k=60)

    assert fused[0] == (B, pytest.approx(2 / 62))
    assert {chunk_id for chunk_id, _ in fused[1:]} == {A, C}


def test_missing_from_a_ranking_contributes_nothing() -> None:
    fused = dict(reciprocal_rank_fusion([[A], []], k=60))

    assert fused[A] == pytest.approx(1 / 61)


def test_symmetric_rankings_tie() -> None:
    fused = dict(reciprocal_rank_fusion([[A, B], [B, A]], k=60))

    assert fused[A] == pytest.approx(fused[B])


def test_sorted_best_first() -> None:
    fused = reciprocal_rank_fusion([[A, B, C]], k=60)

    assert [chunk_id for chunk_id, _ in fused] == [A, B, C]


def test_empty_rankings() -> None:
    assert reciprocal_rank_fusion([[], []]) == []
