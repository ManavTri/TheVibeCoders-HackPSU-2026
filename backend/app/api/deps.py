from typing import Annotated, Any
from uuid import NAMESPACE_URL, UUID, uuid5

from fastapi import Depends

from app.core.auth import current_user

CurrentUser = Annotated[dict[str, Any], Depends(current_user)]


def current_user_id(user: dict[str, Any]) -> str:
    user_id = user.get("sub")
    if not isinstance(user_id, str) or not user_id:
        raise ValueError("Authenticated user token does not contain a valid subject.")
    if user.get("auth_provider") == "auth0":
        return str(uuid5(NAMESPACE_URL, f"muni:auth0:{user_id}"))
    return user_id
