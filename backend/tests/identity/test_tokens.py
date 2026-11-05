from datetime import timedelta
from uuid import uuid4

import jwt
import pytest

from langex.identity.adapters.tokens import JwtAccessTokens
from langex.identity.domain.errors import AuthenticationError
from tests.conftest import START

SECRET = "s" * 40


def test_round_trip() -> None:
    tokens = JwtAccessTokens(SECRET)
    account = uuid4()
    assert tokens.verify(tokens.issue(account, START), START) == account


def test_short_secret_is_refused() -> None:
    with pytest.raises(ValueError, match="32 bytes"):
        JwtAccessTokens("short")


def test_expired_token_is_rejected() -> None:
    tokens = JwtAccessTokens(SECRET, ttl=timedelta(minutes=15))
    token = tokens.issue(uuid4(), START)
    assert tokens.verify(token, START + timedelta(minutes=15))  # within leeway
    with pytest.raises(AuthenticationError) as error:
        tokens.verify(token, START + timedelta(minutes=16))
    assert "expired" in error.value.reason
    assert str(error.value) == "Authentication failed"  # nothing leaks to clients


def test_token_from_the_future_is_rejected() -> None:
    tokens = JwtAccessTokens(SECRET)
    token = tokens.issue(uuid4(), START + timedelta(hours=1))
    with pytest.raises(AuthenticationError, match="Authentication failed"):
        tokens.verify(token, START)


@pytest.mark.parametrize(
    "forge",
    [
        lambda claims: jwt.encode(claims, "x" * 40, algorithm="HS256"),  # wrong key
        lambda claims: jwt.encode(claims, None, algorithm="none"),  # alg=none attack
        lambda claims: jwt.encode({**claims, "aud": "other"}, SECRET, algorithm="HS256"),
        lambda claims: jwt.encode({**claims, "iss": "evil"}, SECRET, algorithm="HS256"),
        lambda claims: jwt.encode({**claims, "sub": "not-a-uuid"}, SECRET, algorithm="HS256"),
        lambda claims: "garbage",
    ],
)
def test_forged_tokens_are_rejected(forge: object) -> None:
    tokens = JwtAccessTokens(SECRET)
    claims = jwt.decode(tokens.issue(uuid4(), START), options={"verify_signature": False})
    with pytest.raises(AuthenticationError):
        tokens.verify(forge(claims), START)  # type: ignore[operator]
