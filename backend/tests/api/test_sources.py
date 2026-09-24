from unittest.mock import AsyncMock, MagicMock
from uuid import UUID

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.sources import router
from app.auth.dependencies import CurrentUser, get_current_user

ANCHOR = UUID(int=1)
BEFORE = UUID(int=2)


@pytest.fixture
def retriever():
    return MagicMock(read_surrounding=AsyncMock())


@pytest.fixture
def client(retriever):
    app = FastAPI()
    app.include_router(router)
    app.state.retriever = retriever
    app.dependency_overrides[get_current_user] = lambda: CurrentUser(id="user-1", email=None, access_token="t")
    return TestClient(app)


def test_returns_anchor_with_context_in_document_order(client, retriever, make_passage) -> None:
    retriever.read_surrounding.return_value = [
        make_passage(
            chunk_id=BEFORE,
            chunk_index=6,
            content="| Receita  |   208,1 |\n|----------|---------|",
        ),
        make_passage(chunk_id=ANCHOR, chunk_index=7),
    ]

    response = client.get(f"/sources/{ANCHOR}?radius=1")

    assert response.status_code == 200
    body = response.json()
    retriever.read_surrounding.assert_awaited_once_with(ANCHOR, 1)
    assert (body["chunkId"], body["ticker"], body["fiscalYear"]) == (
        str(ANCHOR),
        "VALE3",
        2023,
    )
    assert body["referencePeriod"] == "2023-12-31"
    assert [(c["chunkIndex"], c["isAnchor"]) for c in body["chunks"]] == [
        (6, False),
        (7, True),
    ]
    # Table padding is squeezed, matching the text the agent quoted from.
    assert body["chunks"][0]["content"] == "| Receita | 208,1 |\n|---|---|"


def test_unknown_chunk_is_404(client, retriever) -> None:
    retriever.read_surrounding.return_value = []

    assert client.get(f"/sources/{ANCHOR}").status_code == 404


def test_radius_is_bounded(client) -> None:
    assert client.get(f"/sources/{ANCHOR}?radius=10").status_code == 422


def test_requires_auth(retriever) -> None:
    app = FastAPI()
    app.include_router(router)
    app.state.retriever = retriever

    assert TestClient(app).get(f"/sources/{ANCHOR}").status_code == 401
