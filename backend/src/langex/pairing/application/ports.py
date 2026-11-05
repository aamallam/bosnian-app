"""Ports the pairing use cases depend on."""

from __future__ import annotations

from datetime import datetime
from typing import Protocol
from uuid import UUID

from langex.pairing.domain.exchange import Attempt, Contribution
from langex.pairing.domain.invitation import Invitation
from langex.pairing.domain.pair import Pair


class InvitationRepository(Protocol):
    def add(self, invitation: Invitation) -> None: ...

    def save(self, invitation: Invitation) -> None: ...

    def find_by_code_hash(self, code_hash: str) -> Invitation | None: ...


class PairRepository(Protocol):
    def add(self, pair: Pair) -> None: ...

    def get(self, pair_id: UUID) -> Pair | None: ...

    def for_member(self, user_id: UUID) -> list[Pair]: ...


class ContributionRepository(Protocol):
    def add(self, contribution: Contribution) -> None: ...

    def for_pair(self, pair_id: UUID, since: datetime) -> list[Contribution]:
        """Contributions created at or after `since`, oldest first."""
        ...

    def count_by_author_since(self, author_id: UUID, since: datetime) -> int: ...


class AttemptRepository(Protocol):
    def add(self, attempt: Attempt) -> None: ...

    def save(self, attempt: Attempt) -> None: ...

    def get(self, attempt_id: UUID) -> Attempt | None: ...

    def awaiting_review_by(self, reviewer_id: UUID) -> list[Attempt]: ...

    def by_learner(self, pair_id: UUID, learner_id: UUID) -> list[Attempt]: ...
