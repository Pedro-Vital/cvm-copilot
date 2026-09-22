import pytest
from fastapi import HTTPException

from app.database.chats import get_thread_or_403_404


class _FakeResponse:
    def __init__(self, data: dict | None) -> None:
        self.data = data


class _FakeQuery:
    """Stands in for the Supabase fluent query builder used by get_thread_or_403_404."""

    def __init__(self, data: dict | None) -> None:
        self._data = data

    def select(self, *args, **kwargs) -> "_FakeQuery":
        return self

    def eq(self, *args, **kwargs) -> "_FakeQuery":
        return self

    def maybe_single(self) -> "_FakeQuery":
        return self

    async def execute(self) -> _FakeResponse:
        return _FakeResponse(self._data)


class _FakeClient:
    def __init__(self, data: dict | None) -> None:
        self._data = data

    def table(self, name: str) -> _FakeQuery:
        return _FakeQuery(self._data)


@pytest.mark.anyio
async def test_get_thread_or_403_404_not_found() -> None:
    client = _FakeClient(None)

    with pytest.raises(HTTPException) as exc_info:
        await get_thread_or_403_404(client, "thread-1", "user-1")

    assert exc_info.value.status_code == 404


@pytest.mark.anyio
async def test_get_thread_or_403_404_wrong_owner() -> None:
    client = _FakeClient({"id": "thread-1", "user_id": "someone-else"})

    with pytest.raises(HTTPException) as exc_info:
        await get_thread_or_403_404(client, "thread-1", "user-1")

    assert exc_info.value.status_code == 403


@pytest.mark.anyio
async def test_get_thread_or_403_404_returns_owned_thread() -> None:
    client = _FakeClient({"id": "thread-1", "user_id": "user-1"})

    thread = await get_thread_or_403_404(client, "thread-1", "user-1")

    assert thread == {"id": "thread-1", "user_id": "user-1"}
