"""PostgreSQL (SQLAlchemy Core) repositories for the learning context."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import (
    Column,
    Connection,
    Float,
    ForeignKey,
    Index,
    Integer,
    SmallInteger,
    String,
    Table,
    Uuid,
    func,
    select,
    update,
)

from langex.learning.domain.card import MemoryState, Phase, ReviewCard, ReviewLog
from langex.platform.sql import UtcDateTime, new_metadata

metadata = new_metadata()

cards = Table(
    "learning_cards",
    metadata,
    Column("id", Uuid, primary_key=True),
    Column("learner_id", Uuid, nullable=False),
    Column("item_id", Uuid, nullable=False),
    Column("due", UtcDateTime, nullable=False),
    Column("phase", String(16), nullable=False),
    Column("step", Integer),
    Column("stability", Float),
    Column("difficulty", Float),
    Column("last_review", UtcDateTime),
    Column("first_reviewed_at", UtcDateTime),
    Index("uq_learning_cards_learner_item", "learner_id", "item_id", unique=True),
    Index("ix_learning_cards_learner_due", "learner_id", "due"),
)

review_logs = Table(
    "learning_review_logs",
    metadata,
    Column("id", Uuid, primary_key=True),
    Column("card_id", Uuid, ForeignKey("learning_cards.id", ondelete="CASCADE"), nullable=False),
    Column("learner_id", Uuid, nullable=False, index=True),
    Column("rating", SmallInteger, nullable=False),
    Column("reviewed_at", UtcDateTime, nullable=False),
    Column("duration_ms", Integer),
)


def _card(row: Any) -> ReviewCard:
    return ReviewCard(
        id=row.id,
        learner_id=row.learner_id,
        item_id=row.item_id,
        due=row.due,
        memory=MemoryState(
            phase=Phase(row.phase),
            step=row.step,
            stability=row.stability,
            difficulty=row.difficulty,
        ),
        last_review=row.last_review,
    )


def _memory_values(card: ReviewCard) -> dict[str, Any]:
    return {
        "due": card.due,
        "phase": card.memory.phase.value,
        "step": card.memory.step,
        "stability": card.memory.stability,
        "difficulty": card.memory.difficulty,
        "last_review": card.last_review,
    }


class SqlCardRepository:
    def __init__(self, connection: Connection) -> None:
        self._db = connection

    def add(self, card: ReviewCard) -> None:
        self._db.execute(
            cards.insert().values(
                id=card.id,
                learner_id=card.learner_id,
                item_id=card.item_id,
                first_reviewed_at=card.last_review,
                **_memory_values(card),
            )
        )

    def save(self, card: ReviewCard) -> None:
        result = self._db.execute(
            update(cards)
            .where(cards.c.id == card.id)
            .values(
                first_reviewed_at=func.coalesce(cards.c.first_reviewed_at, card.last_review),
                **_memory_values(card),
            )
        )
        if result.rowcount != 1:
            raise KeyError(card.id)

    def get(self, card_id: UUID) -> ReviewCard | None:
        row = self._db.execute(select(cards).where(cards.c.id == card_id)).first()
        return None if row is None else _card(row)

    def find_by_item(self, learner_id: UUID, item_id: UUID) -> ReviewCard | None:
        row = self._db.execute(
            select(cards).where(cards.c.learner_id == learner_id, cards.c.item_id == item_id)
        ).first()
        return None if row is None else _card(row)

    def due(self, learner_id: UUID, now: datetime, limit: int) -> list[ReviewCard]:
        rows = self._db.execute(
            select(cards)
            .where(
                cards.c.learner_id == learner_id,
                cards.c.last_review.is_not(None),
                cards.c.due <= now,
            )
            .order_by(cards.c.due)
            .limit(limit)
        )
        return [_card(row) for row in rows]

    def new(self, learner_id: UUID, limit: int) -> list[ReviewCard]:
        rows = self._db.execute(
            select(cards)
            .where(cards.c.learner_id == learner_id, cards.c.last_review.is_(None))
            .order_by(cards.c.due)
            .limit(limit)
        )
        return [_card(row) for row in rows]

    def count_new_reviewed_since(self, learner_id: UUID, since: datetime) -> int:
        count = self._db.scalar(
            select(func.count()).where(
                cards.c.learner_id == learner_id, cards.c.first_reviewed_at >= since
            )
        )
        return int(count or 0)


class SqlReviewLogRepository:
    def __init__(self, connection: Connection) -> None:
        self._db = connection

    def add(self, log: ReviewLog) -> None:
        self._db.execute(
            review_logs.insert().values(
                id=uuid4(),
                card_id=log.card_id,
                learner_id=log.learner_id,
                rating=int(log.rating),
                reviewed_at=log.reviewed_at,
                duration_ms=log.duration_ms,
            )
        )
