"""Auth-scoped routes. `/auth/me` exists to verify the bearer-token flow end to end."""

from typing import Annotated

from fastapi import APIRouter, Depends

from app.auth.dependencies import CurrentUser, get_current_user

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/me")
async def me(current_user: Annotated[CurrentUser, Depends(get_current_user)]) -> dict[str, str | None]:
    return {"id": current_user.id, "email": current_user.email}
