"""Composition root: builds the services and routes events between contexts.

This is the only module allowed to import more than one context. The API
app factory and worker entry points will build on `build_in_memory` with
Postgres-backed adapters swapped in.
"""

from __future__ import annotations

from dataclasses import dataclass

from langex.bootstrap.event_bus import InMemoryEventBus
from langex.languages.adapters.entry_points import discover_profiles
from langex.languages.application.registry import LanguageRegistry
from langex.learning.adapters.fsrs_scheduler import FsrsScheduler
from langex.learning.adapters.in_memory import InMemoryCardRepository, InMemoryReviewLogRepository
from langex.learning.application.reviews import LearningService
from langex.pairing.adapters.in_memory import (
    InMemoryAttemptRepository,
    InMemoryContributionRepository,
    InMemoryInvitationRepository,
    InMemoryPairRepository,
)
from langex.pairing.application.service import PairingService
from langex.pairing.domain.events import AttemptCorrected, ContributionAdded
from langex.shared_kernel.clock import Clock, SystemClock


@dataclass(frozen=True, slots=True)
class Container:
    languages: LanguageRegistry
    pairing: PairingService
    learning: LearningService
    events: InMemoryEventBus


def wire_events(events: InMemoryEventBus, learning: LearningService) -> None:
    """Pairing → learning: what a partner teaches or corrects becomes practice."""
    events.subscribe(
        ContributionAdded, lambda e: learning.start_learning(e.learner_id, e.contribution_id)
    )
    events.subscribe(
        AttemptCorrected, lambda e: learning.start_learning(e.learner_id, e.attempt_id)
    )


def build_in_memory(clock: Clock | None = None, *, fuzzing: bool = True) -> Container:
    clock = clock or SystemClock()
    events = InMemoryEventBus()
    learning = LearningService(
        cards=InMemoryCardRepository(),
        logs=InMemoryReviewLogRepository(),
        scheduler=FsrsScheduler(enable_fuzzing=fuzzing),
        clock=clock,
    )
    pairing = PairingService(
        invitations=InMemoryInvitationRepository(),
        pairs=InMemoryPairRepository(),
        contributions=InMemoryContributionRepository(),
        attempts=InMemoryAttemptRepository(),
        events=events,
        clock=clock,
    )
    wire_events(events, learning)
    return Container(
        languages=LanguageRegistry(discover_profiles()),
        pairing=pairing,
        learning=learning,
        events=events,
    )
