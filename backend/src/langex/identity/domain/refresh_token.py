"""Rotating refresh tokens with reuse detection (OAuth 2.0 Security BCP).

Each refresh returns a new token and retires the old one. Tokens from one
sign-in form a family. Presenting a retired token again means it was copied
or replayed, so the whole family is revoked and the device must sign in again.
"""

from __future__ import annotations

import hashlib
import secrets
from dataclasses import dataclass, replace
from datetime import datetime, timedelta
from uuid import UUID, uuid4

_TOKEN_BYTES = 32  # 256 bits


def hash_token(token: str) -> str:
    """SHA-256 suffices for high-entropy random tokens (no slow hash needed)."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


@dataclass(frozen=True, slots=True, kw_only=True)
class RefreshToken:
    id: UUID
    account_id: UUID
    family_id: UUID
    token_hash: str
    issued_at: datetime
    expires_at: datetime
    used_at: datetime | None = None
    revoked_at: datetime | None = None

    def __post_init__(self) -> None:
        if self.expires_at <= self.issued_at:
            raise ValueError("A refresh token must expire after it is issued")

    @classmethod
    def issue(
        cls,
        account_id: UUID,
        now: datetime,
        ttl: timedelta,
        family_id: UUID | None = None,
    ) -> tuple[RefreshToken, str]:
        """Return the record to store and the token to give the client once."""
        token = secrets.token_urlsafe(_TOKEN_BYTES)
        record = cls(
            id=uuid4(),
            account_id=account_id,
            family_id=family_id or uuid4(),
            token_hash=hash_token(token),
            issued_at=now,
            expires_at=now + ttl,
        )
        return record, token

    def is_usable(self, now: datetime) -> bool:
        return self.used_at is None and self.revoked_at is None and now < self.expires_at

    @property
    def was_used(self) -> bool:
        return self.used_at is not None

    def used(self, now: datetime) -> RefreshToken:
        return replace(self, used_at=now)

    def revoked(self, now: datetime) -> RefreshToken:
        return self if self.revoked_at is not None else replace(self, revoked_at=now)
