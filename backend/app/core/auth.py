from typing import Annotated, Any
from uuid import UUID

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import get_settings

bearer = HTTPBearer(auto_error=False)


def current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
) -> dict[str, Any]:
    settings = get_settings()
    supabase_is_configured = bool(settings.supabase_url or settings.supabase_service_key)
    if not settings.require_auth and not supabase_is_configured and credentials is None:
        return {"sub": "local-demo", "email": "demo@localhost"}
    if credentials is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Bearer token required")
    if not settings.supabase_jwt_secret:
        raise RuntimeError("A SUPABASE_JWT_SECRET is required to verify access tokens")
    try:
        claims = jwt.decode(
            credentials.credentials,
            settings.supabase_jwt_secret,
            algorithms=["HS256"],
            audience=settings.supabase_jwt_audience,
        )
        try:
            UUID(claims["sub"])
        except (KeyError, TypeError, ValueError) as exc:
            raise jwt.InvalidTokenError("Token is missing a valid user subject") from exc
        return claims
    except jwt.InvalidTokenError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid access token") from exc
