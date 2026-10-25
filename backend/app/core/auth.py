
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
    # Cache signing keys to avoid fetching them for every request.
    return jwt.PyJWKClient(jwks_url)


def _decode_auth0(token: str, settings: Settings) -> dict[str, Any]:
    if not settings.auth0_domain or not settings.auth0_audience:
        raise jwt.InvalidTokenError("Auth0 settings are missing")

    domain = settings.auth0_domain.removeprefix("https://").rstrip("/")
    jwks_url = f"https://{domain}/.well-known/jwks.json"
    key = _jwks_client(jwks_url).get_signing_key_from_jwt(token).key

    return jwt.decode(
        token,
        key,
        algorithms=["RS256"],
        audience=settings.auth0_audience,
        issuer=f"https://{domain}/",
    )


def _decode_supabase(token: str, settings: Settings) -> dict[str, Any]:
    alg = jwt.get_unverified_header(token).get("alg")

    if alg == "HS256":
        if not settings.supabase_jwt_secret:
            raise jwt.InvalidTokenError(
                "HS256 token but SUPABASE_JWT_SECRET is not set"
            )
        key: Any = settings.supabase_jwt_secret
    elif alg in ASYMMETRIC_ALGS:
        if not settings.supabase_url:
            raise jwt.InvalidTokenError(
                "Asymmetric token but SUPABASE_URL is not set"
            )
        jwks_url = (
            f"{settings.supabase_url.rstrip('/')}"
            "/auth/v1/.well-known/jwks.json"
        )
        key = _jwks_client(jwks_url).get_signing_key_from_jwt(token).key
    else:
        raise jwt.InvalidTokenError(f"Unsupported token algorithm: {alg}")

    return jwt.decode(
        token,
        key,
        algorithms=[alg],
        audience=settings.supabase_jwt_audience,
    )


def current_user(
    credentials: Annotated[
        HTTPAuthorizationCredentials | None, Depends(bearer)
    ],
) -> dict[str, Any]:
    settings = get_settings()

    auth_is_configured = bool(
        settings.supabase_url
        or settings.supabase_service_key
        or settings.auth0_domain
        or settings.auth0_audience
    )

    if (
        not settings.require_auth
        and not auth_is_configured
        and credentials is None
    ):
        return {"sub": "local-demo", "email": "demo@localhost"}

    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Bearer token required",
        )

    try:
        token = credentials.credentials

        # Read the issuer only to select the appropriate validator.
        unverified_claims = jwt.decode(
            token,
            options={
                "verify_signature": False,
                "verify_aud": False,
                "verify_iss": False,
            },
        )
        issuer = unverified_claims.get("iss", "")

        if (
            settings.auth0_domain
            and issuer
            == f"https://{settings.auth0_domain.removeprefix('https://').rstrip('/')}/"
        ):
            claims = _decode_auth0(token, settings)
        else:
            claims = _decode_supabase(token, settings)

        subject = claims.get("sub")
        if not isinstance(subject, str) or not subject.strip():
            raise jwt.InvalidTokenError(
                "Token is missing a valid user subject"
            )
        try:
            UUID(subject)
        except ValueError as exc:
            raise jwt.InvalidTokenError(
                "Token is missing a valid user subject"
            ) from exc

        return claims

    except jwt.PyJWTError as exc:
        logger.warning("Rejected access token: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid access token",
        ) from exc
