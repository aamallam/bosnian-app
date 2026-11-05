"""Contract tests: the in-memory and SQL repositories behave the same.

Each test runs once per backend, through the real use cases, so the SQL
adapters are checked against the behaviour the domain tests rely on.
"""

from __future__ import annotations

from collections.abc import Callable, Iterator
from datetime import timedelta
from uuid import uuid4

import pytest
from sqlalchemy import Connection

from langex.bootstrap.container import (
    DEV_SECRET,
    Container,
    Infrastructure,
    Repositories,
    assemble,
    in_memory_repositories,
    sql_repositories,
)
from langex.identity.adapters.oidc import DevVerifier
from langex.identity.adapters.tokens import JwtAccessTokens
from langex.identity.domain.account import Account, ExternalIdentity, Provider
from langex.identity.domain.errors import AuthenticationError
from langex.identity.domain.refresh_token import RefreshToken
from langex.languages.application.registry import LanguageRegistry
from langex.learning.adapters.fsrs_scheduler import FsrsScheduler
from langex.learning.domain.card import MemoryState, Phase, Rating, ReviewCard
from langex.pairing.domain.errors import InvitationError, PairingError
from langex.pairing.domain.invitation import Invitation
from langex.shared_kernel.language import LanguageCode
from tests.conftest import START, FakeClock

AR, BS, EN = LanguageCode("ar"), LanguageCode("bs"), LanguageCode("en")


@pytest.fixture(params=["memory", "sql"])
def make_repos(
    request: pytest.FixtureRequest,
) -> Iterator[Callable[[], Repositories]]:
    if request.param == "memory":
        repos = in_memory_repositories()
        yield lambda: repos
    else:
        connection: Connection = request.getfixturevalue("connection")
        yield lambda: sql_repositories(connection)


@pytest.fixture
def clock() -> FakeClock:
    return FakeClock()


@pytest.fixture
def app(make_repos: Callable[[], Repositories], clock: FakeClock) -> Container:
    infra = Infrastructure(
        clock=clock,
        languages=LanguageRegistry(),
        scheduler=FsrsScheduler(enable_fuzzing=False),
        access_tokens=JwtAccessTokens(DEV_SECRET),
        verifiers={Provider.DEV: DevVerifier()},
    )
    return assemble(make_repos(), infra)


def test_a_week_of_exchange_round_trips(app: Container, clock: FakeClock) -> None:
    me, friend = uuid4(), uuid4()
    pair = app.pairing.accept(friend, app.pairing.invite(me, AR, BS))
    assert app.pairing.pairs_of(me) == [pair]
    assert app.pairing.pairs_of(friend) == [pair]

    minute = timedelta(minutes=1)
    for _ in range(3):  # three days, three sentences each (the default goal)
        for _ in range(3):
            app.pairing.contribute(
                me, pair.id, "  صباح   الخير ", gloss="Good morning", gloss_language=EN
            )
            clock.advance(minute)
            app.pairing.contribute(friend, pair.id, "Dobro jutro", note="Until about 10 am")
            clock.advance(minute)
        clock.advance(timedelta(days=1) - 6 * minute)

    stored = app.pairing.contributions(me, pair.id, START)
    assert len(stored) == 18
    assert stored[0].text == "صباح الخير"
    assert stored[0].gloss_language == EN
    assert stored[0].created_at == START  # timezone-aware UTC survives the database
    assert stored[1].note == "Until about 10 am"
    assert app.pairing.contributions(me, pair.id, START + timedelta(days=2))[0].created_at == (
        START + timedelta(days=2)
    )
    assert app.pairing.streak(me, pair.id) == 3

    session = app.learning.session(friend)
    assert len(session) == 9
    reviewed = app.learning.submit(friend, session[0].id, Rating.GOOD, duration_ms=2100)
    assert reviewed.memory.stability is not None
    assert app.learning.session(friend)[0].id != reviewed.id  # rescheduled, not due now


def test_attempt_and_correction_round_trip(app: Container) -> None:
    me, friend = uuid4(), uuid4()
    pair = app.pairing.accept(friend, app.pairing.invite(me, AR, BS))
    attempt = app.pairing.submit_attempt(me, pair.id, "Ja sam dobro")
    assert app.pairing.to_review(friend) == [attempt]

    corrected = app.pairing.correct(friend, attempt.id, "Dobro sam", "Word order")

    assert app.pairing.to_review(friend) == []
    assert corrected.correction is not None
    assert app.pairing.my_attempts(me, pair.id) == [corrected]
    assert [c.item_id for c in app.learning.session(me)] == [attempt.id]
    with pytest.raises(PairingError):
        app.pairing.correct(friend, attempt.id, "Dobro sam", None)


def test_invitation_cannot_be_redeemed_twice_even_from_a_stale_copy(
    make_repos: Callable[[], Repositories],
) -> None:
    repos = make_repos()
    invitation, _ = Invitation.issue(uuid4(), AR, BS, START)
    repos.invitations.add(invitation)
    stale = repos.invitations.find_by_code_hash(invitation.code_hash)
    assert stale == invitation

    first, _ = invitation.redeem(uuid4(), START)
    repos.invitations.save(first)
    assert stale is not None
    second, _ = stale.redeem(uuid4(), START)  # a concurrent request read it earlier

    if isinstance(repos.invitations, type(in_memory_repositories().invitations)):
        pytest.skip("only the database enforces single use under concurrency")
    with pytest.raises(InvitationError):
        repos.invitations.save(second)


def test_refresh_tokens_round_trip(app: Container, clock: FakeClock) -> None:
    signed_in = app.identity.sign_in(Provider.DEV, "dev:amina")
    assert app.identity.sign_in(Provider.DEV, "dev:amina").account_id == signed_in.account_id
    rotated = app.identity.refresh(signed_in.refresh_token)
    with pytest.raises(AuthenticationError):
        app.identity.refresh(signed_in.refresh_token)
    with pytest.raises(AuthenticationError):
        app.identity.refresh(rotated.refresh_token)
    assert app.identity.authenticate(rotated.access_token) == signed_in.account_id


def test_concurrent_refresh_with_one_token_lets_only_one_win(
    make_repos: Callable[[], Repositories],
) -> None:
    repos = make_repos()
    signed_in_account = uuid4()
    repos.accounts.add(
        Account(
            id=signed_in_account, identity=ExternalIdentity(Provider.DEV, "x"), created_at=START
        )
    )
    record, _ = RefreshToken.issue(signed_in_account, START, timedelta(days=1))
    repos.refresh_tokens.add(record)
    repos.refresh_tokens.save(record.used(START))
    if isinstance(repos.refresh_tokens, type(in_memory_repositories().refresh_tokens)):
        pytest.skip("only the database guards concurrent use")
    with pytest.raises(AuthenticationError):
        repos.refresh_tokens.save(record.used(START + timedelta(seconds=1)))


def test_cards_round_trip_and_count_first_reviews(
    make_repos: Callable[[], Repositories],
) -> None:
    repos = make_repos()
    learner = uuid4()
    card = ReviewCard.new(learner, uuid4(), START)
    repos.cards.add(card)
    assert repos.cards.get(card.id) == card
    assert repos.cards.find_by_item(learner, card.item_id) == card
    assert repos.cards.new(learner, 10) == [card]
    assert repos.cards.due(learner, START, 10) == []

    later = START + timedelta(hours=1)
    reviewed = card.rescheduled(MemoryState(Phase.REVIEW, None, 2.5, 5.0), later, START)
    repos.cards.save(reviewed)
    repos.cards.save(reviewed.rescheduled(reviewed.memory, later, START + timedelta(minutes=5)))

    assert repos.cards.new(learner, 10) == []
    assert repos.cards.due(learner, later, 10)[0].memory.stability == 2.5
    assert repos.cards.count_new_reviewed_since(learner, START) == 1
    assert repos.cards.count_new_reviewed_since(learner, START + timedelta(minutes=1)) == 0
    assert repos.cards.get(uuid4()) is None
    with pytest.raises(KeyError):
        repos.cards.save(ReviewCard.new(learner, uuid4(), START))
