"""Base type for domain events, the way bounded contexts talk to each other.

Example: pairing emits `ContributionAdded`; the composition root routes it
to learning, which creates a review card. Neither context imports the other.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Protocol
from uuid import UUID, uuid4


@dataclass(frozen=True, slots=True, kw_only=True)
class DomainEvent:
    event_id: UUID = field(default_factory=uuid4)
    occurred_at: datetime = field(default_factory=lambda: datetime.now(UTC))


class EventPublisher(Protocol):
    """Port for publishing events. In-process today; a transactional outbox
    plus a queue later, so an event is never lost if a handler fails."""

    def publish(self, event: DomainEvent) -> None: ...
