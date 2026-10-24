from typing import Annotated, Any

from fastapi import Depends

from app.core.auth import current_user

CurrentUser = Annotated[dict[str, Any], Depends(current_user)]


def current_user_id(user: dict[str, Any]) -> str:
    user_id = user.get("sub")
    if not isinstance(user_id, str) or not user_id:
        raise ValueError("Authenticated user token does not contain a valid subject.")
    return user_id
