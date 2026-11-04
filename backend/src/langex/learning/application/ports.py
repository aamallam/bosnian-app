"""Ports the learning use cases depend on; adapters implement them."""

from __future__ import annotations

from datetime import datetime
from typing import Protocol
from uuid import UUID

from langex.learning.domain.card import Rating, ReviewCard, ReviewLog


class Scheduler(Protocol):
    """Spaced-repetition algorithm (FSRS in production)."""

    def schedule(self, card: ReviewCard, rating: Rating, reviewed_at: datetime) -> ReviewCard: ...

    def retrievability(self, card: ReviewCard, at: datetime) -> float:
        """Probability (0..1) that the learner still remembers the item."""
        ...


class CardRepository(Protocol):
    def add(self, card: ReviewCard) -> None: ...

    def save(self, card: ReviewCard) -> None: ...

    def get(self, card_id: UUID) -> ReviewCard | None: ...

    def find_by_item(self, learner_id: UUID, item_id: UUID) -> ReviewCard | None: ...

    def due(self, learner_id: UUID, now: datetime, limit: int) -> list[ReviewCard]:
        """Cards already seen and due now, most overdue first."""
        ...

    def new(self, learner_id: UUID, limit: int) -> list[ReviewCard]:
        """Cards never reviewed, oldest first."""
        ...

    def count_new_reviewed_since(self, learner_id: UUID, since: datetime) -> int: ...


class ReviewLogRepository(Protocol):
    def add(self, log: ReviewLog) -> None: ...
