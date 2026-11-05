"""PostgreSQL (SQLAlchemy Core) repositories for the identity context."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import Column, Connection, ForeignKey, Index, String, Table, Uuid, select, update

from langex.identity.domain.account import Account, ExternalIdentity, Provider
from langex.identity.domain.errors import AuthenticationError
from langex.identity.domain.refresh_token import RefreshToken
from langex.platform.sql import UtcDateTime, new_metadata

metadata = new_metadata()

accounts = Table(
    "identity_accounts",
    metadata,
    Column("id", Uuid, primary_key=True),
    Column("provider", String(16), nullable=False),
    Column("subject", String(255), nullable=False),
    Column("created_at", UtcDateTime, nullable=False),
    Index("uq_identity_accounts_provider_subject", "provider", "subject", unique=True),
)

refresh_tokens = Table(
    "identity_refresh_tokens",
    metadata,
    Column("id", Uuid, primary_key=True),
    Column(
        "account_id", Uuid, ForeignKey("identity_accounts.id", ondelete="CASCADE"), nullable=False
    ),
    Column("family_id", Uuid, nullable=False, index=True),
    Column("token_hash", String(64), nullable=False, unique=True),
    Column("issued_at", UtcDateTime, nullable=False),
    Column("expires_at", UtcDateTime, nullable=False),
    Column("used_at", UtcDateTime),
    Column("revoked_at", UtcDateTime),
)


def _account(row: Any) -> Account:
    return Account(
        id=row.id,
        identity=ExternalIdentity(Provider(row.provider), row.subject),
        created_at=row.created_at,
    )


def _token(row: Any) -> RefreshToken:
    return RefreshToken(
        id=row.id,
        account_id=row.account_id,
        family_id=row.family_id,
        token_hash=row.token_hash,
        issued_at=row.issued_at,
        expires_at=row.expires_at,
        used_at=row.used_at,
        revoked_at=row.revoked_at,
    )


class SqlAccountRepository:
    def __init__(self, connection: Connection) -> None:
        self._db = connection

    def add(self, account: Account) -> None:
        self._db.execute(
            accounts.insert().values(
                id=account.id,
                provider=account.identity.provider.value,
                subject=account.identity.subject,
                created_at=account.created_at,
            )
        )

    def get(self, account_id: UUID) -> Account | None:
        row = self._db.execute(select(accounts).where(accounts.c.id == account_id)).first()
        return None if row is None else _account(row)

    def find_by_identity(self, identity: ExternalIdentity) -> Account | None:
        row = self._db.execute(
            select(accounts).where(
                accounts.c.provider == identity.provider.value,
                accounts.c.subject == identity.subject,
            )
        ).first()
        return None if row is None else _account(row)


class SqlRefreshTokenRepository:
    def __init__(self, connection: Connection) -> None:
        self._db = connection

    def add(self, token: RefreshToken) -> None:
        self._db.execute(
            refresh_tokens.insert().values(
                id=token.id,
                account_id=token.account_id,
                family_id=token.family_id,
                token_hash=token.token_hash,
                issued_at=token.issued_at,
                expires_at=token.expires_at,
                used_at=token.used_at,
                revoked_at=token.revoked_at,
            )
        )

    def save(self, token: RefreshToken) -> None:
        statement = (
            update(refresh_tokens)
            .where(refresh_tokens.c.id == token.id)
            .values(used_at=token.used_at, revoked_at=token.revoked_at)
        )
        if token.used_at is not None and token.revoked_at is None:
            # Two concurrent refreshes with one token: only the first may win.
            statement = statement.where(refresh_tokens.c.used_at.is_(None))
        if self._db.execute(statement).rowcount != 1:
            raise AuthenticationError("refresh token was used concurrently")

    def find_by_hash(self, token_hash: str) -> RefreshToken | None:
        row = self._db.execute(
            select(refresh_tokens).where(refresh_tokens.c.token_hash == token_hash)
        ).first()
        return None if row is None else _token(row)

    def family(self, family_id: UUID) -> list[RefreshToken]:
        rows = self._db.execute(
            select(refresh_tokens).where(refresh_tokens.c.family_id == family_id)
        )
        return [_token(row) for row in rows]
