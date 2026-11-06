"""In-memory repositories for tests and local prototyping."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from langex.identity.domain.account import Account, ExternalIdentity
from langex.identity.domain.refresh_token import RefreshToken


class InMemoryAccountRepository:
    def __init__(self) -> None:
        self._items: dict[UUID, Account] = {}

    def add(self, account: Account) -> None:
        self._items[account.id] = account

    def get(self, account_id: UUID) -> Account | None:
        return self._items.get(account_id)

    def find_by_identity(self, identity: ExternalIdentity) -> Account | None:
        return next((a for a in self._items.values() if a.identity == identity), None)


class InMemoryRefreshTokenRepository:
    def __init__(self) -> None:
        self._items: dict[UUID, RefreshToken] = {}

    def add(self, token: RefreshToken) -> None:
        self._items[token.id] = token

    def save(self, token: RefreshToken) -> None:
        self._items[token.id] = token

    def find_by_hash(self, token_hash: str) -> RefreshToken | None:
        return next((t for t in self._items.values() if t.token_hash == token_hash), None)

    def family(self, family_id: UUID) -> list[RefreshToken]:
        return [t for t in self._items.values() if t.family_id == family_id]


class InMemoryNonceRepository:
    def __init__(self) -> None:
        self._items: dict[str, datetime] = {}

    def add(self, nonce_hash: str, expires_at: datetime) -> None:
        self._items[nonce_hash] = expires_at

    def consume(self, nonce_hash: str, now: datetime) -> bool:
        expires_at = self._items.pop(nonce_hash, None)
        return expires_at is not None and expires_at > now

    def purge_expired(self, now: datetime) -> None:
        self._items = {h: e for h, e in self._items.items() if e > now}
