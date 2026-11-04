"""Events the pairing context publishes for other contexts to react to."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from langex.shared_kernel.events import DomainEvent
from langex.shared_kernel.language import LanguageCode


@dataclass(frozen=True, slots=True, kw_only=True)
class PairFormed(DomainEvent):
    pair_id: UUID
    member_ids: tuple[UUID, UUID]


@dataclass(frozen=True, slots=True, kw_only=True)
class ContributionAdded(DomainEvent):
    """A partner taught something: the learner should start learning it."""

    pair_id: UUID
    contribution_id: UUID
    author_id: UUID
    learner_id: UUID
    language: LanguageCode


@dataclass(frozen=True, slots=True, kw_only=True)
class AttemptCorrected(DomainEvent):
    """A partner corrected the learner's sentence: practise the right version."""

    pair_id: UUID
    attempt_id: UUID
    learner_id: UUID
    language: LanguageCode
