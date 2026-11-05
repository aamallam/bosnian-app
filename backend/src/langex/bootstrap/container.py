"""Composition root: builds the services and routes events between contexts.

This is the only package allowed to import more than one context.
`build_in_memory` serves tests and prototypes; `SqlContainerFactory` builds
one container per database transaction (one per API request), so a use case
and the event handlers it triggers commit or roll back together.
"""

from __future__ import annotations

import secrets
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import timedelta

from sqlalchemy import Connection

from langex.bootstrap.event_bus import InMemoryEventBus
from langex.bootstrap.settings import Settings
from langex.identity.adapters.in_memory import (
    InMemoryAccountRepository,
    InMemoryRefreshTokenRepository,
)
from langex.identity.adapters.oidc import APPLE, GOOGLE, DevVerifier, OidcVerifier
from langex.identity.adapters.sql import SqlAccountRepository, SqlRefreshTokenRepository
from langex.identity.adapters.tokens import JwtAccessTokens
from langex.identity.application.ports import (
    AccessTokens,
    AccountRepository,
    IdTokenVerifier,
    RefreshTokenRepository,
)
from langex.identity.application.service import IdentityService
from langex.identity.domain.account import Provider
from langex.languages.adapters.entry_points import discover_profiles
from langex.languages.application.registry import LanguageRegistry
from langex.learning.adapters.fsrs_scheduler import FsrsScheduler
from langex.learning.adapters.in_memory import InMemoryCardRepository, InMemoryReviewLogRepository
from langex.learning.adapters.sql import SqlCardRepository, SqlReviewLogRepository
from langex.learning.application.ports import CardRepository, ReviewLogRepository
from langex.learning.application.reviews import LearningService
from langex.pairing.adapters.in_memory import (
    InMemoryAttemptRepository,
    InMemoryContributionRepository,
    InMemoryInvitationRepository,
    InMemoryPairRepository,
)
from langex.pairing.adapters.sql import (
    SqlAttemptRepository,
    SqlContributionRepository,
    SqlInvitationRepository,
    SqlPairRepository,
)
from langex.pairing.application.ports import (
    AttemptRepository,
    ContributionRepository,
    InvitationRepository,
    PairRepository,
)
from langex.pairing.application.service import PairingService
from langex.pairing.domain.events import AttemptCorrected, ContributionAdded
from langex.shared_kernel.clock import Clock, SystemClock

# In-memory containers sign tokens with a fresh random key per process.
DEV_SECRET = secrets.token_urlsafe(48)


@dataclass(frozen=True, slots=True)
class Container:
    languages: LanguageRegistry
    identity: IdentityService
    pairing: PairingService
    learning: LearningService
    events: InMemoryEventBus


@dataclass(frozen=True, slots=True)
class Repositories:
    accounts: AccountRepository
    refresh_tokens: RefreshTokenRepository
    invitations: InvitationRepository
    pairs: PairRepository
    contributions: ContributionRepository
    attempts: AttemptRepository
    cards: CardRepository
    logs: ReviewLogRepository


@dataclass(frozen=True, slots=True)
class Infrastructure:
    """Long-lived, stateless pieces shared by every container."""

    clock: Clock
    languages: LanguageRegistry
    scheduler: FsrsScheduler
    access_tokens: AccessTokens
    verifiers: Mapping[Provider, IdTokenVerifier]
    refresh_ttl: timedelta = timedelta(days=30)


def wire_events(events: InMemoryEventBus, learning: LearningService) -> None:
    """Pairing to learning: what a partner teaches or corrects becomes practice."""
    events.subscribe(
        ContributionAdded, lambda e: learning.start_learning(e.learner_id, e.contribution_id)
    )
    events.subscribe(
        AttemptCorrected, lambda e: learning.start_learning(e.learner_id, e.attempt_id)
    )


def assemble(repos: Repositories, infra: Infrastructure) -> Container:
    events = InMemoryEventBus()
    learning = LearningService(
        cards=repos.cards, logs=repos.logs, scheduler=infra.scheduler, clock=infra.clock
    )
    pairing = PairingService(
        invitations=repos.invitations,
        pairs=repos.pairs,
        contributions=repos.contributions,
        attempts=repos.attempts,
        events=events,
        clock=infra.clock,
    )
    identity = IdentityService(
        accounts=repos.accounts,
        refresh_tokens=repos.refresh_tokens,
        access_tokens=infra.access_tokens,
        verifiers=infra.verifiers,
        clock=infra.clock,
        refresh_ttl=infra.refresh_ttl,
    )
    wire_events(events, learning)
    return Container(
        languages=infra.languages,
        identity=identity,
        pairing=pairing,
        learning=learning,
        events=events,
    )


def verifiers_from(settings: Settings) -> dict[Provider, IdTokenVerifier]:
    verifiers: dict[Provider, IdTokenVerifier] = {}
    if settings.google_client_ids:
        verifiers[Provider.GOOGLE] = OidcVerifier(GOOGLE, settings.google_client_ids)
    if settings.apple_client_ids:
        verifiers[Provider.APPLE] = OidcVerifier(APPLE, settings.apple_client_ids)
    if settings.allow_dev_sign_in:
        verifiers[Provider.DEV] = DevVerifier()
    return verifiers


def infrastructure_from(
    settings: Settings,
    clock: Clock | None = None,
    verifiers: Mapping[Provider, IdTokenVerifier] | None = None,
) -> Infrastructure:
    return Infrastructure(
        clock=clock or SystemClock(),
        languages=LanguageRegistry(discover_profiles()),
        scheduler=FsrsScheduler(),
        access_tokens=JwtAccessTokens(
            settings.jwt_secret.get_secret_value(),
            ttl=timedelta(minutes=settings.access_token_minutes),
        ),
        verifiers=verifiers if verifiers is not None else verifiers_from(settings),
        refresh_ttl=timedelta(days=settings.refresh_token_days),
    )


def sql_repositories(connection: Connection) -> Repositories:
    return Repositories(
        accounts=SqlAccountRepository(connection),
        refresh_tokens=SqlRefreshTokenRepository(connection),
        invitations=SqlInvitationRepository(connection),
        pairs=SqlPairRepository(connection),
        contributions=SqlContributionRepository(connection),
        attempts=SqlAttemptRepository(connection),
        cards=SqlCardRepository(connection),
        logs=SqlReviewLogRepository(connection),
    )


def in_memory_repositories() -> Repositories:
    return Repositories(
        accounts=InMemoryAccountRepository(),
        refresh_tokens=InMemoryRefreshTokenRepository(),
        invitations=InMemoryInvitationRepository(),
        pairs=InMemoryPairRepository(),
        contributions=InMemoryContributionRepository(),
        attempts=InMemoryAttemptRepository(),
        cards=InMemoryCardRepository(),
        logs=InMemoryReviewLogRepository(),
    )


def build_in_memory(clock: Clock | None = None, *, fuzzing: bool = True) -> Container:
    infra = Infrastructure(
        clock=clock or SystemClock(),
        languages=LanguageRegistry(discover_profiles()),
        scheduler=FsrsScheduler(enable_fuzzing=fuzzing),
        access_tokens=JwtAccessTokens(DEV_SECRET),
        verifiers={Provider.DEV: DevVerifier()},
    )
    return assemble(in_memory_repositories(), infra)
