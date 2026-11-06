"""Ports the identity use cases depend on."""

from __future__ import annotations

from datetime import datetime
from typing import Protocol
from uuid import UUID

from langex.identity.domain.account import Account, ExternalIdentity
from langex.identity.domain.refresh_token import RefreshToken


class IdTokenVerifier(Protocol):
    """Checks an OpenID Connect ID token from one provider (signature,
    issuer, audience, expiry, nonce) and returns the verified subject."""

    def verify(self, id_token: str, nonce: str | None, now: datetime) -> str: ...


class AccessTokens(Protocol):
    """Short-lived bearer tokens for API calls."""

    def issue(self, account_id: UUID, now: datetime) -> str: ...

    def verify(self, token: str, now: datetime) -> UUID: ...


class AccountRepository(Protocol):
    def add(self, account: Account) -> None: ...

    def get(self, account_id: UUID) -> Account | None: ...

    def find_by_identity(self, identity: ExternalIdentity) -> Account | None: ...


class NonceRepository(Protocol):
    """Single-use sign-in nonces, stored as SHA-256 hashes."""

    def add(self, nonce_hash: str, expires_at: datetime) -> None: ...

    def consume(self, nonce_hash: str, now: datetime) -> bool:
        """Remove the nonce; True only if it existed and had not expired."""
        ...

    def purge_expired(self, now: datetime) -> None: ...


class RefreshTokenRepository(Protocol):
    def add(self, token: RefreshToken) -> None: ...

    def save(self, token: RefreshToken) -> None: ...

    def find_by_hash(self, token_hash: str) -> RefreshToken | None: ...

    def family(self, family_id: UUID) -> list[RefreshToken]: ...
