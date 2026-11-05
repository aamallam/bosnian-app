from datetime import timedelta
from typing import Any

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa

from langex.identity.adapters.oidc import APPLE, GOOGLE, DevVerifier, OidcVerifier
from langex.identity.domain.errors import AuthenticationError
from tests.conftest import START

PRIVATE_KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)
OTHER_KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)
CLIENT_ID = "com.example.langex"
NONCE = "n-0S6_WzA2Mj"


def _id_token(key: Any = PRIVATE_KEY, algorithm: str = "RS256", **overrides: Any) -> str:
    claims: dict[str, Any] = {
        "iss": "https://appleid.apple.com",
        "aud": CLIENT_ID,
        "sub": "001234.abcd",
        "iat": int(START.timestamp()),
        "exp": int((START + timedelta(minutes=10)).timestamp()),
        "nonce": NONCE,
    }
    claims.update(overrides)
    claims = {k: v for k, v in claims.items() if v is not None}
    return jwt.encode(claims, key, algorithm=algorithm)


def _verifier(provider: Any = APPLE) -> OidcVerifier:
    return OidcVerifier(provider, [CLIENT_ID], key_resolver=lambda _: PRIVATE_KEY.public_key())


def test_valid_token_returns_subject() -> None:
    assert _verifier().verify(_id_token(), NONCE, START) == "001234.abcd"


def test_google_accepts_both_issuer_spellings() -> None:
    for issuer in ("https://accounts.google.com", "accounts.google.com"):
        assert _verifier(GOOGLE).verify(_id_token(iss=issuer), NONCE, START)


@pytest.mark.parametrize(
    ("token", "nonce", "reason"),
    [
        (_id_token(aud="someone-else"), NONCE, "audience"),
        (_id_token(iss="https://evil.example"), NONCE, "issuer"),
        (_id_token(key=OTHER_KEY), NONCE, "Signature"),
        (_id_token(key="h" * 40, algorithm="HS256"), NONCE, "alg"),
        (_id_token(nonce="other"), NONCE, "nonce mismatch"),
        (_id_token(nonce=None), NONCE, "nonce mismatch"),
        (_id_token(), None, "nonce is required"),
        (_id_token(sub=None), NONCE, "sub"),
        (_id_token(iat=int((START + timedelta(hours=1)).timestamp())), NONCE, "future"),
    ],
)
def test_invalid_tokens_are_rejected(token: str, nonce: str | None, reason: str) -> None:
    with pytest.raises(AuthenticationError) as error:
        _verifier().verify(token, nonce, START)
    assert reason.lower() in error.value.reason.lower()


def test_expired_token_is_rejected() -> None:
    with pytest.raises(AuthenticationError, match="Authentication failed"):
        _verifier().verify(_id_token(), NONCE, START + timedelta(hours=1))


def test_a_client_id_is_required() -> None:
    with pytest.raises(ValueError, match="client ID"):
        OidcVerifier(APPLE, [], key_resolver=lambda _: None)


def test_dev_verifier() -> None:
    assert DevVerifier().verify("dev:amina", None, START) == "amina"
    for bad in ("amina", "dev:", "prod:amina"):
        with pytest.raises(AuthenticationError):
            DevVerifier().verify(bad, None, START)
