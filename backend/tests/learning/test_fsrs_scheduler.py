"""Behaviour of the FSRS adapter, including property-based checks."""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from langex.learning.adapters.fsrs_scheduler import FsrsScheduler
from langex.learning.domain.card import Phase, Rating, ReviewCard

NOW = datetime(2026, 11, 4, 9, 0, tzinfo=UTC)
SCHEDULER = FsrsScheduler(enable_fuzzing=False)


def _graduated_card() -> ReviewCard:
    """A card that has left the learning phase."""
    card = ReviewCard.new(uuid4(), uuid4(), NOW)
    return SCHEDULER.schedule(card, Rating.EASY, NOW)


def test_new_card_moves_through_learning_steps() -> None:
    card = SCHEDULER.schedule(ReviewCard.new(uuid4(), uuid4(), NOW), Rating.GOOD, NOW)

    assert card.memory.phase is Phase.LEARNING
    assert card.due - NOW < timedelta(hours=1)  # short step, same session
    assert card.memory.stability is not None


def test_easy_graduates_to_review_in_days() -> None:
    card = _graduated_card()

    assert card.memory.phase is Phase.REVIEW
    assert card.due - NOW >= timedelta(days=1)


def test_forgetting_a_review_card_relearns() -> None:
    card = _graduated_card()
    forgot = SCHEDULER.schedule(card, Rating.AGAIN, card.due)

    assert forgot.memory.phase is Phase.RELEARNING
    assert forgot.due - card.due < timedelta(hours=1)


def test_retrievability_falls_over_time() -> None:
    card = _graduated_card()
    soon = SCHEDULER.retrievability(card, NOW + timedelta(days=1))
    later = SCHEDULER.retrievability(card, NOW + timedelta(days=60))

    assert 0 < later < soon <= 1


def test_rejects_unreasonable_retention() -> None:
    with pytest.raises(ValueError, match="retention"):
        FsrsScheduler(desired_retention=0.99)


def test_accepts_custom_parameters() -> None:
    from fsrs import Scheduler  # default weights of the library

    weights = Scheduler().parameters
    scheduler = FsrsScheduler(parameters=weights, enable_fuzzing=False)
    card = ReviewCard.new(uuid4(), uuid4(), NOW)
    assert scheduler.schedule(card, Rating.GOOD, NOW) == SCHEDULER.schedule(card, Rating.GOOD, NOW)


@settings(max_examples=50, deadline=None)
@given(
    ratings=st.lists(st.sampled_from(list(Rating)), min_size=1, max_size=15),
    delays=st.lists(st.integers(min_value=0, max_value=60 * 24 * 90), min_size=15, max_size=15),
)
def test_any_review_history_keeps_card_valid(ratings: list[Rating], delays: list[int]) -> None:
    card = ReviewCard.new(uuid4(), uuid4(), NOW)
    at = NOW
    for rating, delay_minutes in zip(ratings, delays, strict=False):
        at = max(at, card.due) + timedelta(minutes=delay_minutes)
        card = SCHEDULER.schedule(card, rating, at)

        assert card.due >= at
        assert card.last_review == at
        assert card.memory.stability is not None
        assert card.memory.stability > 0
        assert card.memory.difficulty is not None
        assert 1 <= card.memory.difficulty <= 10


@settings(max_examples=30, deadline=None)
@given(days_late=st.integers(min_value=0, max_value=365))
def test_better_ratings_never_give_shorter_intervals(days_late: int) -> None:
    card = _graduated_card()
    at = card.due + timedelta(days=days_late)
    intervals = [SCHEDULER.schedule(card, r, at).due - at for r in Rating]

    assert intervals == sorted(intervals)
