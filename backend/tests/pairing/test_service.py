from datetime import timedelta
from uuid import UUID, uuid4

import pytest

from langex.bootstrap.event_bus import InMemoryEventBus
from langex.pairing.application import service as service_module
from langex.pairing.application.service import PairingService
from langex.pairing.domain.errors import (
    AttemptNotFoundError,
    DailyLimitReachedError,
    InvitationError,
    PairNotFoundError,
)
from langex.pairing.domain.events import AttemptCorrected, ContributionAdded, PairFormed
from langex.pairing.domain.pair import Pair
from tests.pairing.conftest import ARABIC, BOSNIAN, ENGLISH, START, FakeClock


def test_accepting_forms_a_pair_and_announces_it(
    pair: Pair, events: InMemoryEventBus, arabic_speaker: UUID, bosnian_speaker: UUID
) -> None:
    assert pair.membership_of(bosnian_speaker).teaches == BOSNIAN
    assert pair.membership_of(arabic_speaker).learns == BOSNIAN
    assert isinstance(events.published[-1], PairFormed)


def test_unknown_code_is_rejected(service: PairingService) -> None:
    with pytest.raises(InvitationError, match="not valid"):
        service.accept(uuid4(), "made-up-code")


def test_code_cannot_be_reused(service: PairingService) -> None:
    code = service.invite(uuid4(), ARABIC, BOSNIAN)
    service.accept(uuid4(), code)
    with pytest.raises(InvitationError, match="already"):
        service.accept(uuid4(), code)


def test_pairs_are_listed_per_member(
    service: PairingService, pair: Pair, arabic_speaker: UUID
) -> None:
    assert service.pairs_of(arabic_speaker) == [pair]
    assert service.pairs_of(uuid4()) == []


def test_contribution_goes_to_partner_in_authors_language(
    service: PairingService,
    pair: Pair,
    arabic_speaker: UUID,
    bosnian_speaker: UUID,
    events: InMemoryEventBus,
) -> None:
    contribution = service.contribute(
        arabic_speaker,
        pair.id,
        "صباح الخير",
        gloss="Good morning",
        gloss_language=ENGLISH,
        note="Used until about noon",
    )

    assert contribution.language == ARABIC
    assert contribution.learner_id == bosnian_speaker
    event = events.published[-1]
    assert isinstance(event, ContributionAdded)
    assert event.learner_id == bosnian_speaker
    assert event.contribution_id == contribution.id


def test_blank_gloss_and_note_are_dropped(
    service: PairingService, pair: Pair, arabic_speaker: UUID
) -> None:
    contribution = service.contribute(
        arabic_speaker, pair.id, "شكرا", gloss="  ", gloss_language=ENGLISH, note=""
    )
    assert contribution.gloss is None
    assert contribution.gloss_language is None
    assert contribution.note is None


def test_outsiders_cannot_touch_a_pair(service: PairingService, pair: Pair) -> None:
    outsider = uuid4()
    with pytest.raises(PairNotFoundError):
        service.contribute(outsider, pair.id, "Zdravo")
    with pytest.raises(PairNotFoundError):
        service.contributions(outsider, pair.id, START)
    with pytest.raises(PairNotFoundError):
        service.submit_attempt(outsider, pair.id, "Zdravo")
    with pytest.raises(PairNotFoundError):
        service.streak(outsider, pair.id)


def test_unknown_pair_looks_like_foreign_pair(
    service: PairingService, arabic_speaker: UUID
) -> None:
    with pytest.raises(PairNotFoundError):
        service.contribute(arabic_speaker, uuid4(), "Zdravo")


def test_daily_quota_stops_spam(
    service: PairingService, pair: Pair, arabic_speaker: UUID, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(service_module, "MAX_CONTRIBUTIONS_PER_DAY", 3)
    for i in range(3):
        service.contribute(arabic_speaker, pair.id, f"جملة {i}")
    with pytest.raises(DailyLimitReachedError):
        service.contribute(arabic_speaker, pair.id, "جملة أخرى")


def test_attempt_correction_flow(
    service: PairingService,
    pair: Pair,
    arabic_speaker: UUID,
    bosnian_speaker: UUID,
    events: InMemoryEventBus,
) -> None:
    attempt = service.submit_attempt(arabic_speaker, pair.id, "Ja sam dobro")

    assert attempt.language == BOSNIAN
    assert attempt.reviewer_id == bosnian_speaker
    assert service.to_review(bosnian_speaker) == [attempt]

    corrected = service.correct(bosnian_speaker, attempt.id, "Dobro sam.", "Natural word order")

    assert corrected.correction is not None
    assert service.to_review(bosnian_speaker) == []
    event = events.published[-1]
    assert isinstance(event, AttemptCorrected)
    assert event.learner_id == arabic_speaker


def test_learner_cannot_correct_own_attempt(
    service: PairingService, pair: Pair, arabic_speaker: UUID
) -> None:
    attempt = service.submit_attempt(arabic_speaker, pair.id, "Ja sam dobro")
    with pytest.raises(AttemptNotFoundError):
        service.correct(arabic_speaker, attempt.id, "Dobro sam")


def test_outsider_cannot_see_or_correct_attempt(
    service: PairingService, pair: Pair, arabic_speaker: UUID
) -> None:
    attempt = service.submit_attempt(arabic_speaker, pair.id, "Ja sam dobro")
    with pytest.raises(AttemptNotFoundError):
        service.correct(uuid4(), attempt.id, "Dobro sam")
    with pytest.raises(AttemptNotFoundError):
        service.correct(uuid4(), uuid4(), "Dobro sam")


def test_a_week_of_exchange_builds_a_streak(
    service: PairingService,
    pair: Pair,
    clock: FakeClock,
    arabic_speaker: UUID,
    bosnian_speaker: UUID,
) -> None:
    for day in range(7):
        if day == 3:
            # The Bosnian speaker is busy; the Arabic speaker covers with 2x the goal.
            for i in range(4):
                service.contribute(arabic_speaker, pair.id, f"جملة {day}-{i}")
        else:
            for i in range(2):
                service.contribute(arabic_speaker, pair.id, f"جملة {day}-{i}")
                service.contribute(bosnian_speaker, pair.id, f"Rečenica {day}-{i}")
        clock.advance(timedelta(days=1))

    # Day 7 has only started, so it does not break the streak.
    assert service.streak(bosnian_speaker, pair.id) == 7
    since = START + timedelta(days=6)
    assert len(service.contributions(arabic_speaker, pair.id, since)) == 4
