"""PostgreSQL (SQLAlchemy Core) repositories for the pairing context.

Domain objects stay plain frozen dataclasses; this module maps them to rows.
User IDs are plain UUIDs here: other contexts' tables are never referenced.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import (
    Column,
    Connection,
    ForeignKey,
    Index,
    SmallInteger,
    String,
    Table,
    Uuid,
    func,
    select,
    update,
)

from langex.pairing.domain.errors import InvitationError, PairingError
from langex.pairing.domain.exchange import (
    MAX_NOTE_LENGTH,
    MAX_TEXT_LENGTH,
    Attempt,
    Contribution,
    Correction,
)
from langex.pairing.domain.invitation import Invitation
from langex.pairing.domain.pair import Membership, Pair
from langex.platform.sql import UtcDateTime, new_metadata
from langex.shared_kernel.language import LanguageCode

metadata = new_metadata()
_LANG = String(3)

invitations = Table(
    "pairing_invitations",
    metadata,
    Column("id", Uuid, primary_key=True),
    Column("inviter_id", Uuid, nullable=False, index=True),
    Column("inviter_teaches", _LANG, nullable=False),
    Column("inviter_learns", _LANG, nullable=False),
    Column("code_hash", String(64), nullable=False, unique=True),
    Column("created_at", UtcDateTime, nullable=False),
    Column("expires_at", UtcDateTime, nullable=False),
    Column("redeemed_by", Uuid),
    Column("redeemed_at", UtcDateTime),
)

pairs = Table(
    "pairing_pairs",
    metadata,
    Column("id", Uuid, primary_key=True),
    Column("created_at", UtcDateTime, nullable=False),
)

members = Table(
    "pairing_members",
    metadata,
    Column(
        "pair_id",
        Uuid,
        ForeignKey("pairing_pairs.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column("user_id", Uuid, primary_key=True, index=True),
    Column("position", SmallInteger, nullable=False),
    Column("teaches", _LANG, nullable=False),
    Column("learns", _LANG, nullable=False),
)

contributions = Table(
    "pairing_contributions",
    metadata,
    Column("id", Uuid, primary_key=True),
    Column("pair_id", Uuid, ForeignKey("pairing_pairs.id", ondelete="CASCADE"), nullable=False),
    Column("author_id", Uuid, nullable=False),
    Column("learner_id", Uuid, nullable=False),
    Column("language", _LANG, nullable=False),
    Column("text", String(MAX_TEXT_LENGTH), nullable=False),
    Column("created_at", UtcDateTime, nullable=False),
    Column("gloss", String(MAX_TEXT_LENGTH)),
    Column("gloss_language", _LANG),
    Column("note", String(MAX_NOTE_LENGTH)),
    Index("ix_pairing_contributions_pair_created", "pair_id", "created_at"),
    Index("ix_pairing_contributions_author_created", "author_id", "created_at"),
)

attempts = Table(
    "pairing_attempts",
    metadata,
    Column("id", Uuid, primary_key=True),
    Column("pair_id", Uuid, ForeignKey("pairing_pairs.id", ondelete="CASCADE"), nullable=False),
    Column("learner_id", Uuid, nullable=False),
    Column("reviewer_id", Uuid, nullable=False, index=True),
    Column("language", _LANG, nullable=False),
    Column("text", String(MAX_TEXT_LENGTH), nullable=False),
    Column("created_at", UtcDateTime, nullable=False),
    Column("corrected_text", String(MAX_TEXT_LENGTH)),
    Column("correction_comment", String(MAX_NOTE_LENGTH)),
    Column("corrected_at", UtcDateTime),
    Index("ix_pairing_attempts_pair_learner", "pair_id", "learner_id", "created_at"),
)


def _lang(value: str | None) -> LanguageCode | None:
    return None if value is None else LanguageCode(value)


def _invitation(row: Any) -> Invitation:
    return Invitation(
        id=row.id,
        inviter_id=row.inviter_id,
        inviter_teaches=LanguageCode(row.inviter_teaches),
        inviter_learns=LanguageCode(row.inviter_learns),
        code_hash=row.code_hash,
        created_at=row.created_at,
        expires_at=row.expires_at,
        redeemed_by=row.redeemed_by,
        redeemed_at=row.redeemed_at,
    )


def _contribution(row: Any) -> Contribution:
    return Contribution(
        id=row.id,
        pair_id=row.pair_id,
        author_id=row.author_id,
        learner_id=row.learner_id,
        language=LanguageCode(row.language),
        text=row.text,
        created_at=row.created_at,
        gloss=row.gloss,
        gloss_language=_lang(row.gloss_language),
        note=row.note,
    )


def _attempt(row: Any) -> Attempt:
    correction = None
    if row.corrected_at is not None:
        correction = Correction(
            corrected_text=row.corrected_text,
            comment=row.correction_comment,
            corrected_at=row.corrected_at,
        )
    return Attempt(
        id=row.id,
        pair_id=row.pair_id,
        learner_id=row.learner_id,
        reviewer_id=row.reviewer_id,
        language=LanguageCode(row.language),
        text=row.text,
        created_at=row.created_at,
        correction=correction,
    )


class SqlInvitationRepository:
    def __init__(self, connection: Connection) -> None:
        self._db = connection

    def add(self, invitation: Invitation) -> None:
        self._db.execute(
            invitations.insert().values(
                id=invitation.id,
                inviter_id=invitation.inviter_id,
                inviter_teaches=invitation.inviter_teaches.value,
                inviter_learns=invitation.inviter_learns.value,
                code_hash=invitation.code_hash,
                created_at=invitation.created_at,
                expires_at=invitation.expires_at,
                redeemed_by=invitation.redeemed_by,
                redeemed_at=invitation.redeemed_at,
            )
        )

    def save(self, invitation: Invitation) -> None:
        # Guarded update: if two people redeem one code at the same moment,
        # only the first succeeds (single use holds under concurrency).
        result = self._db.execute(
            update(invitations)
            .where(invitations.c.id == invitation.id, invitations.c.redeemed_by.is_(None))
            .values(redeemed_by=invitation.redeemed_by, redeemed_at=invitation.redeemed_at)
        )
        if result.rowcount != 1:
            raise InvitationError("This invitation has already been used")

    def find_by_code_hash(self, code_hash: str) -> Invitation | None:
        row = self._db.execute(
            select(invitations).where(invitations.c.code_hash == code_hash)
        ).first()
        return None if row is None else _invitation(row)


class SqlPairRepository:
    def __init__(self, connection: Connection) -> None:
        self._db = connection

    def add(self, pair: Pair) -> None:
        self._db.execute(pairs.insert().values(id=pair.id, created_at=pair.created_at))
        self._db.execute(
            members.insert(),
            [
                {
                    "pair_id": pair.id,
                    "user_id": m.user_id,
                    "position": position,
                    "teaches": m.teaches.value,
                    "learns": m.learns.value,
                }
                for position, m in enumerate(pair.members)
            ],
        )

    def get(self, pair_id: UUID) -> Pair | None:
        found = self._load([pair_id])
        return found[0] if found else None

    def for_member(self, user_id: UUID) -> list[Pair]:
        ids = self._db.scalars(select(members.c.pair_id).where(members.c.user_id == user_id))
        return self._load(list(ids))

    def _load(self, pair_ids: list[UUID]) -> list[Pair]:
        if not pair_ids:
            return []
        created: dict[UUID, datetime] = {
            row.id: row.created_at
            for row in self._db.execute(
                select(pairs.c.id, pairs.c.created_at).where(pairs.c.id.in_(pair_ids))
            )
        }
        grouped: dict[UUID, list[Membership]] = {pid: [] for pid in created}
        rows = self._db.execute(
            select(members).where(members.c.pair_id.in_(pair_ids)).order_by(members.c.position)
        )
        for row in rows:
            grouped[row.pair_id].append(
                Membership(row.user_id, LanguageCode(row.teaches), LanguageCode(row.learns))
            )
        result = []
        for pid, found in grouped.items():
            first, second = found
            result.append(Pair(id=pid, members=(first, second), created_at=created[pid]))
        return sorted(result, key=lambda p: p.created_at)


class SqlContributionRepository:
    def __init__(self, connection: Connection) -> None:
        self._db = connection

    def add(self, contribution: Contribution) -> None:
        self._db.execute(
            contributions.insert().values(
                id=contribution.id,
                pair_id=contribution.pair_id,
                author_id=contribution.author_id,
                learner_id=contribution.learner_id,
                language=contribution.language.value,
                text=contribution.text,
                created_at=contribution.created_at,
                gloss=contribution.gloss,
                gloss_language=(
                    None
                    if contribution.gloss_language is None
                    else contribution.gloss_language.value
                ),
                note=contribution.note,
            )
        )

    def for_pair(self, pair_id: UUID, since: datetime) -> list[Contribution]:
        rows = self._db.execute(
            select(contributions)
            .where(contributions.c.pair_id == pair_id, contributions.c.created_at >= since)
            .order_by(contributions.c.created_at, contributions.c.id)
        )
        return [_contribution(row) for row in rows]

    def count_by_author_since(self, author_id: UUID, since: datetime) -> int:
        count = self._db.scalar(
            select(func.count()).where(
                contributions.c.author_id == author_id, contributions.c.created_at >= since
            )
        )
        return int(count or 0)


class SqlAttemptRepository:
    def __init__(self, connection: Connection) -> None:
        self._db = connection

    def add(self, attempt: Attempt) -> None:
        self._db.execute(
            attempts.insert().values(
                id=attempt.id,
                pair_id=attempt.pair_id,
                learner_id=attempt.learner_id,
                reviewer_id=attempt.reviewer_id,
                language=attempt.language.value,
                text=attempt.text,
                created_at=attempt.created_at,
            )
        )

    def save(self, attempt: Attempt) -> None:
        correction = attempt.correction
        if correction is None:
            return
        # Guarded update: an attempt is corrected once, even under concurrency.
        result = self._db.execute(
            update(attempts)
            .where(attempts.c.id == attempt.id, attempts.c.corrected_at.is_(None))
            .values(
                corrected_text=correction.corrected_text,
                correction_comment=correction.comment,
                corrected_at=correction.corrected_at,
            )
        )
        if result.rowcount != 1:
            raise PairingError("This attempt has already been corrected")

    def get(self, attempt_id: UUID) -> Attempt | None:
        row = self._db.execute(select(attempts).where(attempts.c.id == attempt_id)).first()
        return None if row is None else _attempt(row)

    def awaiting_review_by(self, reviewer_id: UUID) -> list[Attempt]:
        rows = self._db.execute(
            select(attempts)
            .where(attempts.c.reviewer_id == reviewer_id, attempts.c.corrected_at.is_(None))
            .order_by(attempts.c.created_at)
        )
        return [_attempt(row) for row in rows]

    def by_learner(self, pair_id: UUID, learner_id: UUID) -> list[Attempt]:
        rows = self._db.execute(
            select(attempts)
            .where(attempts.c.pair_id == pair_id, attempts.c.learner_id == learner_id)
            .order_by(attempts.c.created_at)
        )
        return [_attempt(row) for row in rows]
