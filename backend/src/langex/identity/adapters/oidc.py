"""Verification of OpenID Connect ID tokens from Apple and Google.

The mobile app signs in with the platform SDK and sends us the ID token.
We check its signature against the provider's published keys (JWKS) and
check issuer, audience (our client IDs), expiry and nonce ourselves.
"""

from __future__ import annotations

import hmac
from collections.abc import Callable, Collection
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

import jwt

from langex.identity.domain.errors import AuthenticationError

KeyResolver = Callable[[str], Any]
_LEEWAY = timedelta(seconds=60)


@dataclass(frozen=True, slots=True)
class OidcProvider:
    name: str
    issuers: frozenset[str]
    jwks_url: str


GOOGLE = OidcProvider(
    name="google",
    issuers=frozenset({"https://accounts.google.com", "accounts.google.com"}),
    jwks_url="https://www.googleapis.com/oauth2/v3/certs",
)
APPLE = OidcProvider(
    name="apple",
    issuers=frozenset({"https://appleid.apple.com"}),
    jwks_url="https://appleid.apple.com/auth/keys",
)


def jwks_resolver(jwks_url: str) -> KeyResolver:
    """Fetch and cache the provider's signing keys (fixed URL, short timeout)."""
    client = jwt.PyJWKClient(jwks_url, cache_keys=True, lifespan=3600, timeout=5)
    return lambda token: client.get_signing_key_from_jwt(token).key


class OidcVerifier:
    def __init__(
        self,
        provider: OidcProvider,
        audiences: Collection[str],
        key_resolver: KeyResolver | None = None,
    ) -> None:
        if not audiences:
            raise ValueError(f"{provider.name}: at least one client ID is required")
        self._provider = provider
        self._audiences = list(audiences)
        self._resolve_key = key_resolver or jwks_resolver(provider.jwks_url)

    def verify(self, id_token: str, nonce: str | None, now: datetime) -> str:
        if not nonce:
            raise AuthenticationError("nonce is required")
        try:
            key = self._resolve_key(id_token)
            claims = jwt.decode(
                id_token,
                key,
                algorithms=["RS256"],
                audience=self._audiences,
                options={
                    "require": ["iss", "sub", "aud", "exp", "iat"],
                    "verify_iss": False,  # several valid issuers: checked below
                    "verify_exp": False,
                    "verify_iat": False,
                    "verify_nbf": False,
                },
            )
        except (jwt.PyJWTError, ValueError, KeyError) as error:
            raise AuthenticationError(f"{self._provider.name}: {error}") from error
        timestamp = now.timestamp()
        if claims["iss"] not in self._provider.issuers:
            raise AuthenticationError(f"{self._provider.name}: unexpected issuer")
        if claims["exp"] <= timestamp - _LEEWAY.total_seconds():
            raise AuthenticationError(f"{self._provider.name}: token expired")
        if claims["iat"] > timestamp + _LEEWAY.total_seconds():
            raise AuthenticationError(f"{self._provider.name}: token issued in the future")
        if not hmac.compare_digest(str(claims.get("nonce", "")), nonce):
            raise AuthenticationError(f"{self._provider.name}: nonce mismatch")
        return str(claims["sub"])


class DevVerifier:
    """Accepts `dev:<name>` as an ID token. Only for local development and
    tests; settings refuse to enable it in staging and production."""

    def verify(self, id_token: str, nonce: str | None, now: datetime) -> str:
        prefix, _, subject = id_token.partition(":")
        if prefix != "dev" or not subject:
            raise AuthenticationError("dev token must look like dev:<name>")
        return subject
