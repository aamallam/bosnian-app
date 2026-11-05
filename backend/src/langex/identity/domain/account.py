"""Accounts and the external identities (Apple, Google) that sign in to them.

Data minimisation: no name, email or password is stored. An account is an
ID plus the opaque subject the identity provider gave us.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from uuid import UUID, uuid4


class Provider(StrEnum):
    APPLE = "apple"
    GOOGLE = "google"
    DEV = "dev"  # local development and tests only; settings refuse it elsewhere


@dataclass(frozen=True, slots=True)
class ExternalIdentity:
    provider: Provider
    subject: str

    def __post_init__(self) -> None:
        if not self.subject or len(self.subject) > 255:
            raise ValueError("Identity subject must be 1-255 characters")


@dataclass(frozen=True, slots=True, kw_only=True)
class Account:
    id: UUID
    identity: ExternalIdentity
    created_at: datetime

    @classmethod
    def open(cls, identity: ExternalIdentity, now: datetime) -> Account:
        return cls(id=uuid4(), identity=identity, created_at=now)
