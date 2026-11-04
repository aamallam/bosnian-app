from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest

from langex.bootstrap.event_bus import InMemoryEventBus
from langex.pairing.adapters.in_memory import (
    InMemoryAttemptRepository,
    InMemoryContributionRepository,
    InMemoryInvitationRepository,
    InMemoryPairRepository,
)
from langex.pairing.application.service import PairingService
from langex.pairing.domain.pair import Pair
from langex.pairing.domain.streak import DailyGoal
from langex.shared_kernel.language import LanguageCode

ARABIC = LanguageCode("ar")
BOSNIAN = LanguageCode("bs")
ENGLISH = LanguageCode("en")
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
def events() -> InMemoryEventBus:
    return InMemoryEventBus()


@pytest.fixture
def service(clock: FakeClock, events: InMemoryEventBus) -> PairingService:
    return PairingService(
        invitations=InMemoryInvitationRepository(),
        pairs=InMemoryPairRepository(),
        contributions=InMemoryContributionRepository(),
        attempts=InMemoryAttemptRepository(),
        events=events,
        clock=clock,
        goal=DailyGoal(sentences_per_day=2),
    )


@pytest.fixture
def arabic_speaker() -> UUID:
    return uuid4()


@pytest.fixture
def bosnian_speaker() -> UUID:
    return uuid4()


@pytest.fixture
def pair(service: PairingService, arabic_speaker: UUID, bosnian_speaker: UUID) -> Pair:
    code = service.invite(arabic_speaker, teaches=ARABIC, learns=BOSNIAN)
    return service.accept(bosnian_speaker, code)
