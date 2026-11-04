"""Base type for domain events, the way bounded contexts talk to each other.

Example: pairing emits `ContributionAdded`; learning reacts by creating
review cards. Neither context imports the other.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import UUID, uuid4


@dataclass(frozen=True, slots=True, kw_only=True)
class DomainEvent:
    event_id: UUID = field(default_factory=uuid4)
    occurred_at: datetime = field(default_factory=lambda: datetime.now(UTC))
