import logging
from functools import lru_cache
from typing import Annotated, Any
from uuid import UUID

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import Settings, get_settings

logger = logging.getLogger(__name__)
bearer = HTTPBearer(auto_error=False)

ASYMMETRIC_ALGS = {"ES256", "RS256"}


@lru_cache
def _jwks_client(jwks_url: str) -> jwt.PyJWKClient:
    # PyJWKClient caches fetched keys, so this is not a network call per request.
    return jwt.PyJWKClient(jwks_url)


def _decode(token: str, settings: Settings) -> dict[str, Any]:
    alg = jwt.get_unverified_header(token).get("alg")

    if alg == "HS256":
        if not settings.supabase_jwt_secret:
            raise jwt.InvalidTokenError("HS256 token but SUPABASE_JWT_SECRET is not set")
        key: Any = settings.supabase_jwt_secret
    elif alg in ASYMMETRIC_ALGS:
        if not settings.supabase_url:
            raise jwt.InvalidTokenError("Asymmetric token but SUPABASE_URL is not set")
        jwks_url = f"{settings.supabase_url.rstrip('/')}/auth/v1/.well-known/jwks.json"
        key = _jwks_client(jwks_url).get_signing_key_from_jwt(token).key
    else:
        raise jwt.InvalidTokenError(f"Unsupported token algorithm: {alg}")

    return jwt.decode(
        token,
        key,
        algorithms=[alg],  # alg is from the allowlist above, never "none"
        audience=settings.supabase_jwt_audience,
    )


def current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
) -> dict[str, Any]:
    settings = get_settings()
    supabase_is_configured = bool(settings.supabase_url or settings.supabase_service_key)
    if not settings.require_auth and not supabase_is_configured and credentials is None:
        return {"sub": "local-demo", "email": "demo@localhost"}
    if credentials is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Bearer token required")
    try:
        claims = _decode(credentials.credentials, settings)
        try:
            UUID(claims["sub"])
        except (KeyError, TypeError, ValueError) as exc:
            raise jwt.InvalidTokenError("Token is missing a valid user subject") from exc
        return claims
    except jwt.PyJWTError as exc:
        # Log the reason server-side; never log the token itself.
        logger.warning("Rejected access token: %s", exc)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid access token") from exc