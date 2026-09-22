"""Profile persistence via the Supabase client.

profiles has no INSERT policy (see the initial migration) — rows are
written by the backend via the service-role client, keyed by the Supabase
auth user id.
"""

from supabase import AsyncClient

PROFILES_TABLE = "profiles"


async def ensure_profile(service_client: AsyncClient, user_id: str, email: str) -> None:
    await service_client.table(PROFILES_TABLE).upsert({"id": user_id, "email": email}).execute()
