"""Invitation to form a pair: single use, expiring, stored only as a hash."""

from __future__ import annotations

import hashlib
import secrets
from dataclasses import dataclass, replace
from datetime import datetime, timedelta
from uuid import UUID, uuid4

from langex.pairing.domain.errors import InvitationError
from langex.pairing.domain.pair import Membership, Pair
from langex.shared_kernel.language import LanguageCode

INVITATION_TTL = timedelta(days=7)
_CODE_BYTES = 16  # 128 bits: not guessable, even without rate limits


def hash_code(code: str) -> str:
    """SHA-256 is enough here: codes are random and high-entropy, unlike
    passwords, so a slow hash adds nothing. A leaked database row cannot
    be turned back into a working invite link."""
    return hashlib.sha256(code.encode("utf-8")).hexdigest()


@dataclass(frozen=True, slots=True, kw_only=True)
class Invitation:
    id: UUID
    inviter_id: UUID
    inviter_teaches: LanguageCode
    inviter_learns: LanguageCode
    code_hash: str
    created_at: datetime
    expires_at: datetime
    redeemed_by: UUID | None = None
    redeemed_at: datetime | None = None

    def __post_init__(self) -> None:
        if self.inviter_teaches == self.inviter_learns:
            raise ValueError("Teaching and learning languages must differ")
        if self.expires_at <= self.created_at:
            raise ValueError("An invitation must expire after it is created")

    @classmethod
    def issue(
        cls,
        inviter_id: UUID,
        teaches: LanguageCode,
        learns: LanguageCode,
        now: datetime,
    ) -> tuple[Invitation, str]:
        """Return the invitation and its one-time code. The code is shown to
        the inviter once (as a link or QR) and never stored in clear."""
        code = secrets.token_urlsafe(_CODE_BYTES)
        invitation = cls(
            id=uuid4(),
            inviter_id=inviter_id,
            inviter_teaches=teaches,
            inviter_learns=learns,
            code_hash=hash_code(code),
            created_at=now,
            expires_at=now + INVITATION_TTL,
        )
        return invitation, code

    def redeem(self, user_id: UUID, now: datetime) -> tuple[Invitation, Pair]:
        if self.redeemed_by is not None:
            raise InvitationError("This invitation has already been used")
        if now >= self.expires_at:
            raise InvitationError("This invitation has expired")
        if user_id == self.inviter_id:
            raise InvitationError("You cannot accept your own invitation")
        pair = Pair(
            id=uuid4(),
            members=(
                Membership(self.inviter_id, self.inviter_teaches, self.inviter_learns),
                Membership(user_id, self.inviter_learns, self.inviter_teaches),
            ),
            created_at=now,
        )
        return replace(self, redeemed_by=user_id, redeemed_at=now), pair
