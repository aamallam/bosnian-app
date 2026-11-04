"""Use cases: add items to learn, build a review session, record answers."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from uuid import UUID

from langex.languages.domain.matching import MatchLevel
from langex.learning.application.ports import CardRepository, ReviewLogRepository, Scheduler
from langex.learning.domain.card import Rating, ReviewCard, ReviewLog
from langex.shared_kernel.clock import Clock


class CardNotFoundError(LookupError):
    """Raised for missing cards *and* for cards owned by someone else,
    so callers cannot probe which card IDs exist (no IDOR oracle)."""


# A typed answer's grade maps onto a starting rating; the learner may
# still upgrade GOOD to EASY themselves.
RATING_FOR_MATCH: dict[MatchLevel, Rating] = {
    MatchLevel.EXACT: Rating.GOOD,
    MatchLevel.CLOSE: Rating.HARD,
    MatchLevel.WRONG: Rating.AGAIN,
}


@dataclass(frozen=True, slots=True)
class SessionLimits:
    max_reviews: int = 100
    new_per_day: int = 10

    def __post_init__(self) -> None:
        if self.max_reviews < 1 or self.new_per_day < 0:
            raise ValueError("Session limits must be positive")


class LearningService:
    def __init__(
        self,
        cards: CardRepository,
        logs: ReviewLogRepository,
        scheduler: Scheduler,
        clock: Clock,
        limits: SessionLimits | None = None,
    ) -> None:
        self._cards = cards
        self._logs = logs
        self._scheduler = scheduler
        self._clock = clock
        self._limits = limits or SessionLimits()

    def start_learning(self, learner_id: UUID, item_id: UUID) -> ReviewCard:
        """Create a card for an item. Idempotent: the same item twice is one card,
        so a redelivered event (e.g. ContributionAdded) is harmless."""
        existing = self._cards.find_by_item(learner_id, item_id)
        if existing is not None:
            return existing
        card = ReviewCard.new(learner_id, item_id, self._clock.now())
        self._cards.add(card)
        return card

    def session(self, learner_id: UUID) -> list[ReviewCard]:
        """Due reviews first (memory at risk), then today's allowance of new cards.

        "Today" is a rolling 24 hours for now; it becomes the learner's local
        day once learners have a timezone.
        """
        now = self._clock.now()
        due = self._cards.due(learner_id, now, self._limits.max_reviews)
        room = self._limits.max_reviews - len(due)
        new_seen_today = self._cards.count_new_reviewed_since(learner_id, now - timedelta(days=1))
        new_allowance = max(0, min(room, self._limits.new_per_day - new_seen_today))
        return due + self._cards.new(learner_id, new_allowance)

    def submit(
        self,
        learner_id: UUID,
        card_id: UUID,
        rating: Rating,
        duration_ms: int | None = None,
    ) -> ReviewCard:
        card = self._cards.get(card_id)
        if card is None or card.learner_id != learner_id:
            raise CardNotFoundError(card_id)
        now = self._clock.now()
        updated = self._scheduler.schedule(card, rating, now)
        self._cards.save(updated)
        self._logs.add(
            ReviewLog(
                card_id=card.id,
                learner_id=learner_id,
                rating=rating,
                reviewed_at=now,
                duration_ms=duration_ms,
            )
        )
        return updated

    def submit_typed_answer(
        self,
        learner_id: UUID,
        card_id: UUID,
        grade: MatchLevel,
        duration_ms: int | None = None,
    ) -> ReviewCard:
        return self.submit(learner_id, card_id, RATING_FOR_MATCH[grade], duration_ms)
