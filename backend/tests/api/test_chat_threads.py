from unittest.mock import AsyncMock, patch

import pytest
from fastapi import FastAPI, HTTPException, status
from fastapi.testclient import TestClient

from app.api.chat import router
from app.auth.dependencies import CurrentUser, get_current_user

MODULE = "app.api.chat"


@pytest.fixture
def client():
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_current_user] = lambda: CurrentUser(id="user-1", email=None, access_token="t")
    return TestClient(app)


@pytest.fixture
def supabase():
    with (
        patch(f"{MODULE}.get_service_client", AsyncMock()),
        patch(f"{MODULE}.get_user_client", AsyncMock()),
        patch(f"{MODULE}.get_thread_or_403_404", AsyncMock()) as ownership,
        patch(f"{MODULE}.delete_thread", AsyncMock()) as delete,
    ):
        yield ownership, delete


def test_delete_own_thread_returns_204(client, supabase) -> None:
    _, delete = supabase

    response = client.delete("/chat/threads/thread-1")

    assert response.status_code == 204
    assert delete.await_args.args[1] == "thread-1"


def test_delete_foreign_thread_is_forbidden_and_deletes_nothing(client, supabase) -> None:
    ownership, delete = supabase
    ownership.side_effect = HTTPException(status.HTTP_403_FORBIDDEN, "Not your thread")

    response = client.delete("/chat/threads/thread-1")

    assert response.status_code == 403
    delete.assert_not_awaited()
