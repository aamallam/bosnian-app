"""A pair: two people, each teaching their language and learning the other's."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from langex.pairing.domain.errors import PairNotFoundError
from langex.shared_kernel.language import LanguageCode


@dataclass(frozen=True, slots=True)
class Membership:
    user_id: UUID
    teaches: LanguageCode
    learns: LanguageCode

    def __post_init__(self) -> None:
        if self.teaches == self.learns:
            raise ValueError("A member must teach and learn different languages")


@dataclass(frozen=True, slots=True, kw_only=True)
class Pair:
    """Reciprocal by construction: what one member teaches, the other learns.

    Modelled as a list of members so "circles" (one teacher, many learners)
    can extend it later without changing the rest of the context.
    """

    id: UUID
    members: tuple[Membership, Membership]
    created_at: datetime

    def __post_init__(self) -> None:
        first, second = self.members
        if first.user_id == second.user_id:
            raise ValueError("A pair needs two different people")
        if first.teaches != second.learns or second.teaches != first.learns:
            raise ValueError("Each member must learn what the other teaches")

    def is_member(self, user_id: UUID) -> bool:
        return any(m.user_id == user_id for m in self.members)

    def membership_of(self, user_id: UUID) -> Membership:
        for member in self.members:
            if member.user_id == user_id:
                return member
        raise PairNotFoundError(self.id)

    def partner_of(self, user_id: UUID) -> Membership:
        self.membership_of(user_id)  # raises for outsiders
        return next(m for m in self.members if m.user_id != user_id)
