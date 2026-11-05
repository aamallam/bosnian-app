"""In-memory repositories for tests and local prototyping."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from langex.pairing.domain.exchange import Attempt, Contribution
from langex.pairing.domain.invitation import Invitation
from langex.pairing.domain.pair import Pair


class InMemoryInvitationRepository:
    def __init__(self) -> None:
        self._items: dict[UUID, Invitation] = {}

    def add(self, invitation: Invitation) -> None:
        self._items[invitation.id] = invitation

    def save(self, invitation: Invitation) -> None:
        self._items[invitation.id] = invitation

    def find_by_code_hash(self, code_hash: str) -> Invitation | None:
        return next((i for i in self._items.values() if i.code_hash == code_hash), None)


class InMemoryPairRepository:
    def __init__(self) -> None:
        self._items: dict[UUID, Pair] = {}

    def add(self, pair: Pair) -> None:
        self._items[pair.id] = pair

    def get(self, pair_id: UUID) -> Pair | None:
        return self._items.get(pair_id)

    def for_member(self, user_id: UUID) -> list[Pair]:
        return [p for p in self._items.values() if p.is_member(user_id)]


class InMemoryContributionRepository:
    def __init__(self) -> None:
        self._items: list[Contribution] = []

    def add(self, contribution: Contribution) -> None:
        self._items.append(contribution)

    def for_pair(self, pair_id: UUID, since: datetime) -> list[Contribution]:
        found = [c for c in self._items if c.pair_id == pair_id and c.created_at >= since]
        return sorted(found, key=lambda c: c.created_at)

    def count_by_author_since(self, author_id: UUID, since: datetime) -> int:
        return sum(1 for c in self._items if c.author_id == author_id and c.created_at >= since)


class InMemoryAttemptRepository:
    def __init__(self) -> None:
        self._items: dict[UUID, Attempt] = {}

    def add(self, attempt: Attempt) -> None:
        self._items[attempt.id] = attempt

    def save(self, attempt: Attempt) -> None:
        self._items[attempt.id] = attempt

    def get(self, attempt_id: UUID) -> Attempt | None:
        return self._items.get(attempt_id)

    def awaiting_review_by(self, reviewer_id: UUID) -> list[Attempt]:
        found = [
            a for a in self._items.values() if a.reviewer_id == reviewer_id and a.correction is None
        ]
        return sorted(found, key=lambda a: a.created_at)

    def by_learner(self, pair_id: UUID, learner_id: UUID) -> list[Attempt]:
        found = [
            a for a in self._items.values() if a.pair_id == pair_id and a.learner_id == learner_id
        ]
        return sorted(found, key=lambda a: a.created_at)
