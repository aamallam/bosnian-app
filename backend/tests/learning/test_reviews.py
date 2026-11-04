from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest

from langex.languages.domain.matching import MatchLevel
from langex.learning.adapters.fsrs_scheduler import FsrsScheduler
from langex.learning.adapters.in_memory import InMemoryCardRepository, InMemoryReviewLogRepository
from langex.learning.application.reviews import CardNotFoundError, LearningService, SessionLimits
from langex.learning.domain.card import Rating

START = datetime(2026, 11, 4, 9, 0, tzinfo=UTC)


class FakeClock:
    def __init__(self, now: datetime) -> None:
        self.current = now

    def now(self) -> datetime:
        return self.current

    def advance(self, delta: timedelta) -> None:
        self.current += delta


@pytest.fixture
def clock() -> FakeClock:
    return FakeClock(START)


@pytest.fixture
def logs() -> InMemoryReviewLogRepository:
    return InMemoryReviewLogRepository()


@pytest.fixture
def service(clock: FakeClock, logs: InMemoryReviewLogRepository) -> LearningService:
    return LearningService(
        cards=InMemoryCardRepository(),
        logs=logs,
        scheduler=FsrsScheduler(enable_fuzzing=False),
        clock=clock,
        limits=SessionLimits(max_reviews=20, new_per_day=3),
    )


def _add_items(service: LearningService, learner: UUID, count: int) -> None:
    for _ in range(count):
        service.start_learning(learner, uuid4())


def test_starting_same_item_twice_is_idempotent(service: LearningService) -> None:
    learner, item = uuid4(), uuid4()
    assert service.start_learning(learner, item) == service.start_learning(learner, item)


def test_session_limits_new_cards_per_day(service: LearningService) -> None:
    learner = uuid4()
    _add_items(service, learner, 10)

    session = service.session(learner)

    assert len(session) == 3
    assert all(card.is_new for card in session)


def test_new_allowance_is_used_up_by_reviews(service: LearningService) -> None:
    learner = uuid4()
    _add_items(service, learner, 10)
    for card in service.session(learner):
        service.submit(learner, card.id, Rating.EASY)

    assert service.session(learner) == []


def test_new_allowance_returns_next_day(service: LearningService, clock: FakeClock) -> None:
    learner = uuid4()
    _add_items(service, learner, 10)
    for card in service.session(learner):
        service.submit(learner, card.id, Rating.EASY)

    clock.advance(timedelta(days=1, minutes=1))

    assert sum(card.is_new for card in service.session(learner)) == 3


def test_due_reviews_come_before_new_cards(service: LearningService, clock: FakeClock) -> None:
    learner = uuid4()
    _add_items(service, learner, 1)
    first = service.session(learner)[0]
    service.submit(learner, first.id, Rating.GOOD)  # short learning step
    _add_items(service, learner, 2)
    clock.advance(timedelta(hours=1))

    session = service.session(learner)

    assert session[0].id == first.id
    assert [card.is_new for card in session[1:]] == [True, True]


def test_submit_records_a_review_log(
    service: LearningService, logs: InMemoryReviewLogRepository
) -> None:
    learner = uuid4()
    card = service.start_learning(learner, uuid4())

    updated = service.submit(learner, card.id, Rating.GOOD, duration_ms=4200)

    assert updated.last_review == START
    assert len(logs.logs) == 1
    assert logs.logs[0].rating is Rating.GOOD
    assert logs.logs[0].duration_ms == 4200


def test_cannot_review_someone_elses_card(service: LearningService) -> None:
    owner, intruder = uuid4(), uuid4()
    card = service.start_learning(owner, uuid4())

    with pytest.raises(CardNotFoundError):
        service.submit(intruder, card.id, Rating.EASY)


def test_unknown_card_looks_the_same_as_foreign_card(service: LearningService) -> None:
    with pytest.raises(CardNotFoundError):
        service.submit(uuid4(), uuid4(), Rating.GOOD)


@pytest.mark.parametrize(
    ("grade", "rating"),
    [
        (MatchLevel.EXACT, Rating.GOOD),
        (MatchLevel.CLOSE, Rating.HARD),
        (MatchLevel.WRONG, Rating.AGAIN),
    ],
)
def test_typed_answer_grade_maps_to_rating(
    service: LearningService, logs: InMemoryReviewLogRepository, grade: MatchLevel, rating: Rating
) -> None:
    learner = uuid4()
    card = service.start_learning(learner, uuid4())

    service.submit_typed_answer(learner, card.id, grade)

    assert logs.logs[-1].rating is rating


def test_session_limits_must_be_sane() -> None:
    with pytest.raises(ValueError, match="positive"):
        SessionLimits(max_reviews=0)


def test_a_simulated_month_of_daily_practice(clock: FakeClock) -> None:
    """A learner who always answers GOOD meets every item, never gets more than
    the daily new-card allowance, and sees intervals grow beyond a week."""
    cards = InMemoryCardRepository()
    service = LearningService(
        cards=cards,
        logs=InMemoryReviewLogRepository(),
        scheduler=FsrsScheduler(enable_fuzzing=False),
        clock=clock,
        limits=SessionLimits(max_reviews=20, new_per_day=3),
    )
    learner = uuid4()
    _add_items(service, learner, 30)

    for _ in range(30):
        session = service.session(learner)
        assert sum(card.is_new for card in session) <= 3
        while session:
            for card in session:
                service.submit(learner, card.id, Rating.GOOD)
            clock.advance(timedelta(minutes=15))  # finish learning steps in the same sitting
            session = [c for c in service.session(learner) if not c.is_new]
        clock.advance(timedelta(days=1))

    assert cards.new(learner, limit=100) == []
    longest = max(
        c.due - c.last_review
        for c in cards.due(learner, clock.now() + timedelta(days=365), 100)
        if c.last_review is not None
    )
    assert longest > timedelta(days=7)
