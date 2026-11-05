"""Sign-in, token refresh, sign-out and request authentication."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import timedelta
from uuid import UUID

from langex.identity.application.ports import (
    AccessTokens,
    AccountRepository,
    IdTokenVerifier,
    RefreshTokenRepository,
)
from langex.identity.domain.account import Account, ExternalIdentity, Provider
from langex.identity.domain.errors import AuthenticationError
from langex.identity.domain.refresh_token import RefreshToken, hash_token
from langex.shared_kernel.clock import Clock

DEFAULT_REFRESH_TTL = timedelta(days=30)


@dataclass(frozen=True, slots=True)
class TokenPair:
    access_token: str
    refresh_token: str
    account_id: UUID
    is_new_account: bool = False


class IdentityService:
    def __init__(
        self,
        accounts: AccountRepository,
        refresh_tokens: RefreshTokenRepository,
        access_tokens: AccessTokens,
        verifiers: Mapping[Provider, IdTokenVerifier],
        clock: Clock,
        refresh_ttl: timedelta = DEFAULT_REFRESH_TTL,
    ) -> None:
        self._accounts = accounts
        self._refresh_tokens = refresh_tokens
        self._access_tokens = access_tokens
        self._verifiers = verifiers
        self._clock = clock
        self._refresh_ttl = refresh_ttl

    @property
    def providers(self) -> list[Provider]:
        return sorted(self._verifiers)

    def sign_in(self, provider: Provider, id_token: str, nonce: str | None = None) -> TokenPair:
        verifier = self._verifiers.get(provider)
        if verifier is None:
            raise AuthenticationError(f"provider {provider} is not enabled")
        subject = verifier.verify(id_token, nonce, self._clock.now())
        identity = ExternalIdentity(provider, subject)
        account = self._accounts.find_by_identity(identity)
        is_new = account is None
        if account is None:
            account = Account.open(identity, self._clock.now())
            self._accounts.add(account)
        return self._tokens_for(account.id, family_id=None, is_new=is_new)

    def refresh(self, refresh_token: str) -> TokenPair:
        now = self._clock.now()
        record = self._refresh_tokens.find_by_hash(hash_token(refresh_token))
        if record is None:
            raise AuthenticationError("unknown refresh token")
        if record.was_used and record.revoked_at is None:
            self._revoke_family(record.family_id)
            raise AuthenticationError("refresh token reused; family revoked")
        if not record.is_usable(now):
            raise AuthenticationError("refresh token expired or revoked")
        self._refresh_tokens.save(record.used(now))
        return self._tokens_for(record.account_id, family_id=record.family_id)

    def sign_out(self, refresh_token: str) -> None:
        """End this device's session. Unknown tokens are ignored (idempotent)."""
        record = self._refresh_tokens.find_by_hash(hash_token(refresh_token))
        if record is not None:
            self._revoke_family(record.family_id)

    def authenticate(self, access_token: str) -> UUID:
        """Return the account behind a bearer token, or raise."""
        account_id = self._access_tokens.verify(access_token, self._clock.now())
        if self._accounts.get(account_id) is None:
            raise AuthenticationError("account no longer exists")
        return account_id

    def _tokens_for(
        self, account_id: UUID, family_id: UUID | None, *, is_new: bool = False
    ) -> TokenPair:
        now = self._clock.now()
        record, token = RefreshToken.issue(account_id, now, self._refresh_ttl, family_id)
        self._refresh_tokens.add(record)
        return TokenPair(
            access_token=self._access_tokens.issue(account_id, now),
            refresh_token=token,
            account_id=account_id,
            is_new_account=is_new,
        )

    def _revoke_family(self, family_id: UUID) -> None:
        now = self._clock.now()
        for token in self._refresh_tokens.family(family_id):
            if token.revoked_at is None:
                self._refresh_tokens.save(token.revoked(now))
