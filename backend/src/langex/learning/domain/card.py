"""Review card: what one learner remembers about one learning item."""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime
from enum import IntEnum, StrEnum
from uuid import UUID, uuid4


class Rating(IntEnum):
    """How well the learner recalled the item."""

    AGAIN = 1  # forgot
    HARD = 2  # recalled with effort or small errors
    GOOD = 3  # recalled
    EASY = 4  # recalled instantly


class Phase(StrEnum):
    LEARNING = "learning"  # new: short steps (minutes) until it sticks
    REVIEW = "review"  # spaced intervals (days to months)
    RELEARNING = "relearning"  # forgotten after review: short steps again


@dataclass(frozen=True, slots=True)
class MemoryState:
    """Scheduler state. Meaning follows FSRS: stability is in days,
    difficulty is 1 (easy) to 10 (hard); both are unknown for a new card."""

    phase: Phase
    step: int | None
    stability: float | None
    difficulty: float | None

    def __post_init__(self) -> None:
        if self.stability is not None and self.stability <= 0:
            raise ValueError("Stability must be positive")
        if self.difficulty is not None and not 1 <= self.difficulty <= 10:
            raise ValueError("Difficulty must be between 1 and 10")

    @classmethod
    def new(cls) -> MemoryState:
        return cls(phase=Phase.LEARNING, step=0, stability=None, difficulty=None)


@dataclass(frozen=True, slots=True, kw_only=True)
class ReviewCard:
    """Immutable: every review produces a new version of the card.

    `item_id` points at whatever is being learned (a sentence, a correction,
    a word). Learning does not know or care what it is.
    """

    learner_id: UUID
    item_id: UUID
    due: datetime
    memory: MemoryState
    last_review: datetime | None = None
    id: UUID

    def __post_init__(self) -> None:
        if self.due.tzinfo is None:
            raise ValueError("Due date must be timezone-aware")
        if self.last_review is not None and self.last_review.tzinfo is None:
            raise ValueError("Last review must be timezone-aware")

    @classmethod
    def new(cls, learner_id: UUID, item_id: UUID, now: datetime) -> ReviewCard:
        return cls(
            id=uuid4(),
            learner_id=learner_id,
            item_id=item_id,
            due=now,
            memory=MemoryState.new(),
        )

    @property
    def is_new(self) -> bool:
        return self.last_review is None

    def is_due(self, now: datetime) -> bool:
        return self.due <= now

    def rescheduled(self, memory: MemoryState, due: datetime, reviewed_at: datetime) -> ReviewCard:
        if due < reviewed_at:
            raise ValueError("A card cannot be due before it was reviewed")
        return replace(self, memory=memory, due=due, last_review=reviewed_at)


@dataclass(frozen=True, slots=True, kw_only=True)
class ReviewLog:
    """One answer. Kept forever (until account deletion): it is the training
    data for personalising the scheduler and for the mistake fingerprint."""

    card_id: UUID
    learner_id: UUID
    rating: Rating
    reviewed_at: datetime
    duration_ms: int | None = None

    def __post_init__(self) -> None:
        if self.duration_ms is not None and self.duration_ms < 0:
            raise ValueError("Duration cannot be negative")
