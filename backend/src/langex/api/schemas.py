"""Request and response bodies. Inputs forbid unknown fields and cap every
string, so oversized or unexpected payloads fail before reaching use cases."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from langex.identity.domain.account import Provider
from langex.languages.domain.profile import LanguageProfile, TextDirection
from langex.learning.domain.card import Phase, ReviewCard
from langex.pairing.domain.exchange import Attempt, Contribution
from langex.pairing.domain.pair import Pair

LangCode = Annotated[str, StringConstraints(pattern=r"^[a-z]{2,3}$")]
Text = Annotated[str, StringConstraints(min_length=1, max_length=600)]
LongText = Annotated[str, StringConstraints(max_length=1200)]


class Input(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


# ------------------------------------------------------------------ auth
class SignInRequest(Input):
    provider: Provider
    id_token: Annotated[str, StringConstraints(min_length=1, max_length=8192)]
    nonce: Annotated[str, StringConstraints(max_length=256)] | None = None


class NonceResponse(BaseModel):
    nonce: str = Field(description="Pass to Apple or Google, then send it with sign-in")
    expires_in: int = Field(description="Seconds until it can no longer be used")


class RefreshRequest(Input):
    refresh_token: Annotated[str, StringConstraints(min_length=1, max_length=256)]


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: Literal["bearer"] = "bearer"  # noqa: S105 - the OAuth token type, not a secret
    expires_in: int = Field(description="Access token lifetime in seconds")
    account_id: UUID
    is_new_account: bool


class Me(BaseModel):
    id: UUID


# ------------------------------------------------------------- languages
class LanguageOut(BaseModel):
    code: str
    english_name: str
    native_name: str
    direction: TextDirection
    scripts: list[str]

    @classmethod
    def of(cls, profile: LanguageProfile) -> LanguageOut:
        return cls(
            code=profile.code.value,
            english_name=profile.english_name,
            native_name=profile.native_name,
            direction=profile.direction,
            scripts=list(profile.scripts),
        )


# --------------------------------------------------------------- pairing
class InviteRequest(Input):
    teaches: LangCode
    learns: LangCode


class InviteResponse(BaseModel):
    code: str = Field(description="Shown once; share it as a link or QR code")
    expires_in_days: int


class AcceptRequest(Input):
    code: Annotated[str, StringConstraints(min_length=1, max_length=64)]


class MemberOut(BaseModel):
    user_id: UUID
    teaches: str
    learns: str


class PairOut(BaseModel):
    id: UUID
    created_at: datetime
    members: list[MemberOut]

    @classmethod
    def of(cls, pair: Pair) -> PairOut:
        return cls(
            id=pair.id,
            created_at=pair.created_at,
            members=[
                MemberOut(user_id=m.user_id, teaches=m.teaches.value, learns=m.learns.value)
                for m in pair.members
            ],
        )


class ContributionIn(Input):
    text: Text
    gloss: Text | None = None
    gloss_language: LangCode | None = None
    note: LongText | None = None


class ContributionOut(BaseModel):
    id: UUID
    pair_id: UUID
    author_id: UUID
    learner_id: UUID
    language: str
    text: str
    created_at: datetime
    gloss: str | None
    gloss_language: str | None
    note: str | None

    @classmethod
    def of(cls, c: Contribution) -> ContributionOut:
        return cls(
            id=c.id,
            pair_id=c.pair_id,
            author_id=c.author_id,
            learner_id=c.learner_id,
            language=c.language.value,
            text=c.text,
            created_at=c.created_at,
            gloss=c.gloss,
            gloss_language=None if c.gloss_language is None else c.gloss_language.value,
            note=c.note,
        )


class AttemptIn(Input):
    text: Text


class CorrectionIn(Input):
    corrected_text: Text
    comment: LongText | None = None


class CorrectionOut(BaseModel):
    corrected_text: str
    comment: str | None
    corrected_at: datetime


class AttemptOut(BaseModel):
    id: UUID
    pair_id: UUID
    learner_id: UUID
    reviewer_id: UUID
    language: str
    text: str
    created_at: datetime
    correction: CorrectionOut | None

    @classmethod
    def of(cls, a: Attempt) -> AttemptOut:
        correction = None
        if a.correction is not None:
            correction = CorrectionOut(
                corrected_text=a.correction.corrected_text,
                comment=a.correction.comment,
                corrected_at=a.correction.corrected_at,
            )
        return cls(
            id=a.id,
            pair_id=a.pair_id,
            learner_id=a.learner_id,
            reviewer_id=a.reviewer_id,
            language=a.language.value,
            text=a.text,
            created_at=a.created_at,
            correction=correction,
        )


class StreakOut(BaseModel):
    days: int


# -------------------------------------------------------------- learning
class CardOut(BaseModel):
    id: UUID
    item_id: UUID = Field(description="The contribution or attempt being learned")
    due: datetime
    phase: Phase
    is_new: bool

    @classmethod
    def of(cls, card: ReviewCard) -> CardOut:
        return cls(
            id=card.id,
            item_id=card.item_id,
            due=card.due,
            phase=card.memory.phase,
            is_new=card.is_new,
        )


class ReviewIn(Input):
    rating: Annotated[int, Field(ge=1, le=4, description="1 again, 2 hard, 3 good, 4 easy")]
    duration_ms: Annotated[int, Field(ge=0, le=3_600_000)] | None = None
