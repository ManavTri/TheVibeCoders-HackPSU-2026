import time
from uuid import uuid4

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import ec
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

from app.core import auth
from app.core.config import get_settings

AUDIENCE = "authenticated"


class _FakeSigningKey:
    def __init__(self, key):
        self.key = key


class _FakeJwksClient:
    def __init__(self, public_key):
        self._public_key = public_key

    def get_signing_key_from_jwt(self, token):
        return _FakeSigningKey(self._public_key)


@pytest.fixture
def signing_key(monkeypatch):
    """Configure ES256 verification against a freshly generated key pair."""
    monkeypatch.setenv("REQUIRE_AUTH", "true")
    monkeypatch.setenv("SUPABASE_URL", "https://example.supabase.co")
    monkeypatch.setenv("SUPABASE_SERVICE_KEY", "unused-in-auth-tests")
    monkeypatch.setenv("SUPABASE_JWT_AUDIENCE", AUDIENCE)
    get_settings.cache_clear()
    private_key = ec.generate_private_key(ec.SECP256R1())
    monkeypatch.setattr(auth, "_jwks_client", lambda url: _FakeJwksClient(private_key.public_key()))
    yield private_key
    get_settings.cache_clear()


def _token(key, *, sub=None, aud=AUDIENCE, exp_offset=300, alg="ES256"):
    payload = {"aud": aud, "exp": int(time.time()) + exp_offset}
    if sub != "OMIT":
        payload["sub"] = sub or str(uuid4())
    return jwt.encode(payload, key, algorithm=alg, headers={"kid": "test-key"})


def _creds(token):
    return HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)


def _assert_rejected(token):
    with pytest.raises(HTTPException) as exc:
        auth.current_user(_creds(token))
    assert exc.value.status_code == 401


def test_valid_es256_token_is_accepted(signing_key):
    sub = str(uuid4())
    claims = auth.current_user(_creds(_token(signing_key, sub=sub)))
    assert claims["sub"] == sub


def test_token_signed_by_a_different_key_is_rejected(signing_key):
    attacker_key = ec.generate_private_key(ec.SECP256R1())
    _assert_rejected(_token(attacker_key))


def test_wrong_audience_is_rejected(signing_key):
    _assert_rejected(_token(signing_key, aud="someone-else"))


def test_expired_token_is_rejected(signing_key):
    _assert_rejected(_token(signing_key, exp_offset=-60))


def test_non_uuid_subject_is_rejected(signing_key):
    _assert_rejected(_token(signing_key, sub="not-a-uuid"))


def test_missing_subject_is_rejected(signing_key):
    _assert_rejected(_token(signing_key, sub="OMIT"))


def test_unsupported_algorithm_is_rejected(signing_key):
    payload = {"sub": str(uuid4()), "aud": AUDIENCE, "exp": int(time.time()) + 300}
    _assert_rejected(jwt.encode(payload, "x" * 64, algorithm="HS512"))


def test_alg_none_is_rejected(signing_key):
    payload = {"sub": str(uuid4()), "aud": AUDIENCE, "exp": int(time.time()) + 300}
    _assert_rejected(jwt.encode(payload, "", algorithm="none"))