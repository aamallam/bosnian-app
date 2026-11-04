"""End to end through the composition root: what one partner teaches
shows up in the other partner's review session."""

from datetime import UTC, datetime
from uuid import uuid4

from langex.bootstrap.container import build_in_memory
from langex.bootstrap.event_bus import InMemoryEventBus
from langex.learning.domain.card import Rating
from langex.shared_kernel.events import DomainEvent
from langex.shared_kernel.language import LanguageCode


class FakeClock:
    def __init__(self) -> None:
        self.current = datetime(2026, 11, 4, 9, 0, tzinfo=UTC)

    def now(self) -> datetime:
        return self.current


def test_contribution_becomes_partners_review_card() -> None:
    clock = FakeClock()
    app = build_in_memory(clock, fuzzing=False)
    me, friend = uuid4(), uuid4()
    pair = app.pairing.accept(
        friend, app.pairing.invite(me, LanguageCode("ar"), LanguageCode("bs"))
    )

    contribution = app.pairing.contribute(me, pair.id, "صباح الخير")

    friends_session = app.learning.session(friend)
    assert [card.item_id for card in friends_session] == [contribution.id]
    assert app.learning.session(me) == []

    reviewed = app.learning.submit(friend, friends_session[0].id, Rating.GOOD)
    assert reviewed.last_review is not None


def test_corrected_attempt_becomes_learners_review_card() -> None:
    app = build_in_memory(FakeClock(), fuzzing=False)
    me, friend = uuid4(), uuid4()
    pair = app.pairing.accept(
        friend, app.pairing.invite(me, LanguageCode("ar"), LanguageCode("bs"))
    )
    attempt = app.pairing.submit_attempt(me, pair.id, "Ja sam dobro")

    assert app.learning.session(me) == []  # nothing to learn until it is corrected
    app.pairing.correct(friend, attempt.id, "Dobro sam.")

    assert [card.item_id for card in app.learning.session(me)] == [attempt.id]


def test_built_in_languages_are_registered() -> None:
    app = build_in_memory(FakeClock())
    assert app.languages.is_supported(LanguageCode("bs"))
    assert app.languages.is_supported(LanguageCode("ar"))


def test_bus_delivers_only_to_matching_subscribers() -> None:
    class Ping(DomainEvent):
        pass

    class Pong(DomainEvent):
        pass

    bus = InMemoryEventBus()
    received: list[DomainEvent] = []
    bus.subscribe(Ping, received.append)

    bus.publish(Pong())
    bus.publish(ping := Ping())

    assert received == [ping]
    assert len(bus.published) == 2
