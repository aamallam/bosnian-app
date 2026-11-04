"""In-memory repositories for tests and local prototyping."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from langex.learning.domain.card import ReviewCard, ReviewLog


class InMemoryCardRepository:
    def __init__(self) -> None:
        self._cards: dict[UUID, ReviewCard] = {}
        self._first_review: dict[UUID, datetime] = {}

    def add(self, card: ReviewCard) -> None:
        if card.id in self._cards:
            raise ValueError(f"Card {card.id} already exists")
        self._cards[card.id] = card

    def save(self, card: ReviewCard) -> None:
        if card.id not in self._cards:
            raise KeyError(card.id)
        if card.last_review is not None:
            self._first_review.setdefault(card.id, card.last_review)
        self._cards[card.id] = card

    def get(self, card_id: UUID) -> ReviewCard | None:
        return self._cards.get(card_id)

    def find_by_item(self, learner_id: UUID, item_id: UUID) -> ReviewCard | None:
        return next(
            (
                c
                for c in self._cards.values()
                if c.learner_id == learner_id and c.item_id == item_id
            ),
            None,
        )

    def due(self, learner_id: UUID, now: datetime, limit: int) -> list[ReviewCard]:
        cards = [
            c
            for c in self._cards.values()
            if c.learner_id == learner_id and not c.is_new and c.is_due(now)
        ]
        return sorted(cards, key=lambda c: c.due)[:limit]

    def new(self, learner_id: UUID, limit: int) -> list[ReviewCard]:
        cards = [c for c in self._cards.values() if c.learner_id == learner_id and c.is_new]
        return sorted(cards, key=lambda c: c.due)[:limit]

    def count_new_reviewed_since(self, learner_id: UUID, since: datetime) -> int:
        return sum(
            1
            for card_id, first in self._first_review.items()
            if first >= since and self._cards[card_id].learner_id == learner_id
        )


class InMemoryReviewLogRepository:
    def __init__(self) -> None:
        self.logs: list[ReviewLog] = []

    def add(self, log: ReviewLog) -> None:
        self.logs.append(log)
