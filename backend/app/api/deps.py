from typing import Annotated, Any

from fastapi import Depends

from app.core.auth import current_user

CurrentUser = Annotated[dict[str, Any] | None, Depends(current_user)]
