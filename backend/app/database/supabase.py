"""Supabase clients: user-scoped (RLS enforced) and service-role (privileged).

Never reuse the service-role client for a specific user's request — it
bypasses Row Level Security entirely, so any write made with it must
explicitly carry and check the authenticated user's id. See
architecture.md § "Supabase and FastAPI Communication".
"""

import asyncio

from supabase import AsyncClient, AsyncClientOptions, create_async_client

from app.config import settings

_service_client: AsyncClient | None = None
_service_client_lock = asyncio.Lock()


async def get_user_client(access_token: str) -> AsyncClient:
    """A client scoped to one authenticated user's Supabase session.

    Uses the anon key with the user's access token attached, so Postgres
    row-level security policies see the caller as that user.
    """
    return await create_async_client(
        settings.supabase_url,
        settings.supabase_anon_key,
        options=AsyncClientOptions(headers={"Authorization": f"Bearer {access_token}"}),
    )


async def get_service_client() -> AsyncClient:
    """The privileged backend-only client. Bypasses RLS — service-role key only."""
    global _service_client
    if _service_client is None:
        async with _service_client_lock:
            if _service_client is None:
                _service_client = await create_async_client(
                    settings.supabase_url, settings.supabase_service_role_key
                )
    return _service_client
