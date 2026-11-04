from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from langex.learning.domain.card import MemoryState, Phase, Rating, ReviewCard, ReviewLog

NOW = datetime(2026, 11, 4, 9, 0, tzinfo=UTC)


def test_new_card_is_due_immediately_and_unseen() -> None:
    card = ReviewCard.new(uuid4(), uuid4(), NOW)

    assert card.is_new
    assert card.is_due(NOW)
    assert card.memory == MemoryState.new()


def test_rescheduled_returns_new_version() -> None:
    card = ReviewCard.new(uuid4(), uuid4(), NOW)
    memory = MemoryState(Phase.REVIEW, None, stability=3.0, difficulty=5.0)

    later = card.rescheduled(memory, NOW + timedelta(days=3), NOW)

    assert card.is_new  # original unchanged
    assert not later.is_new
    assert not later.is_due(NOW + timedelta(days=2))
    assert later.is_due(NOW + timedelta(days=3))


def test_cannot_be_due_before_review() -> None:
    card = ReviewCard.new(uuid4(), uuid4(), NOW)
    with pytest.raises(ValueError, match="before"):
        card.rescheduled(MemoryState.new(), NOW - timedelta(minutes=1), NOW)


def test_rejects_naive_datetimes() -> None:
    with pytest.raises(ValueError, match="timezone"):
        ReviewCard.new(uuid4(), uuid4(), datetime(2026, 11, 4))
    card = ReviewCard.new(uuid4(), uuid4(), NOW)
    with pytest.raises(ValueError, match="timezone"):
        ReviewCard(
            id=card.id,
            learner_id=card.learner_id,
            item_id=card.item_id,
            due=NOW,
            memory=card.memory,
            last_review=datetime(2026, 11, 4),
        )


@pytest.mark.parametrize(
    ("stability", "difficulty"), [(0.0, 5.0), (-1.0, 5.0), (1.0, 0.5), (1.0, 10.5)]
)
def test_memory_state_bounds(stability: float, difficulty: float) -> None:
    with pytest.raises(ValueError):
        MemoryState(Phase.REVIEW, None, stability, difficulty)


def test_review_log_rejects_negative_duration() -> None:
    with pytest.raises(ValueError, match="negative"):
        ReviewLog(
            card_id=uuid4(), learner_id=uuid4(), rating=Rating.GOOD, reviewed_at=NOW, duration_ms=-1
        )
