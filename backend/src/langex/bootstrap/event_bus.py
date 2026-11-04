"""Synchronous in-process event bus.

Good enough while everything runs in one process and one transaction.
Replaced by a transactional outbox + worker before handlers do slow or
remote work (see ADR 0002).
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Callable
from typing import Any, TypeVar

from langex.shared_kernel.events import DomainEvent

E = TypeVar("E", bound=DomainEvent)
Handler = Callable[[Any], object]


class InMemoryEventBus:
    def __init__(self) -> None:
        self._handlers: defaultdict[type[DomainEvent], list[Handler]] = defaultdict(list)
        self.published: list[DomainEvent] = []

    def subscribe(self, event_type: type[E], handler: Callable[[E], object]) -> None:
        self._handlers[event_type].append(handler)

    def publish(self, event: DomainEvent) -> None:
        self.published.append(event)
        for handler in self._handlers[type(event)]:
            handler(event)
