from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from langex.api.dependencies import CurrentSession
from langex.api.rate_limit import RateLimit
from langex.api.schemas import (
    AcceptRequest,
    AttemptIn,
    AttemptOut,
    ContributionIn,
    ContributionOut,
    CorrectionIn,
    InviteRequest,
    InviteResponse,
    PairOut,
    StreakOut,
)
from langex.pairing.domain.invitation import INVITATION_TTL
from langex.shared_kernel.language import LanguageCode

router = APIRouter(tags=["pairing"], dependencies=[Depends(RateLimit("api"))])


@router.post("/invitations", status_code=status.HTTP_201_CREATED)
def invite(body: InviteRequest, session: CurrentSession) -> InviteResponse:
    with session.begin() as c:
        code = c.pairing.invite(
            session.user_id, LanguageCode(body.teaches), LanguageCode(body.learns)
        )
    return InviteResponse(code=code, expires_in_days=INVITATION_TTL.days)


@router.post("/invitations/accept", status_code=status.HTTP_201_CREATED)
def accept(body: AcceptRequest, session: CurrentSession) -> PairOut:
    with session.begin() as c:
        return PairOut.of(c.pairing.accept(session.user_id, body.code))


@router.get("/pairs")
def pairs(session: CurrentSession) -> list[PairOut]:
    with session.begin() as c:
        return [PairOut.of(p) for p in c.pairing.pairs_of(session.user_id)]


@router.post("/pairs/{pair_id}/contributions", status_code=status.HTTP_201_CREATED)
def contribute(pair_id: UUID, body: ContributionIn, session: CurrentSession) -> ContributionOut:
    with session.begin() as c:
        contribution = c.pairing.contribute(
            session.user_id,
            pair_id,
            body.text,
            gloss=body.gloss,
            gloss_language=None
            if body.gloss_language is None
            else LanguageCode(body.gloss_language),
            note=body.note,
        )
    return ContributionOut.of(contribution)


@router.get("/pairs/{pair_id}/contributions")
def contributions(
    pair_id: UUID,
    session: CurrentSession,
    since: Annotated[datetime | None, Query(description="Only items created at or after")] = None,
) -> list[ContributionOut]:
    start = since or datetime.min.replace(tzinfo=UTC)
    if start.tzinfo is None:
        start = start.replace(tzinfo=UTC)
    with session.begin() as c:
        return [
            ContributionOut.of(x) for x in c.pairing.contributions(session.user_id, pair_id, start)
        ]


@router.post("/pairs/{pair_id}/attempts", status_code=status.HTTP_201_CREATED)
def submit_attempt(pair_id: UUID, body: AttemptIn, session: CurrentSession) -> AttemptOut:
    with session.begin() as c:
        return AttemptOut.of(c.pairing.submit_attempt(session.user_id, pair_id, body.text))


@router.get("/pairs/{pair_id}/attempts")
def my_attempts(pair_id: UUID, session: CurrentSession) -> list[AttemptOut]:
    """The caller's own attempts in this pair, with corrections once given."""
    with session.begin() as c:
        return [AttemptOut.of(a) for a in c.pairing.my_attempts(session.user_id, pair_id)]


@router.get("/pairs/{pair_id}/streak")
def streak(pair_id: UUID, session: CurrentSession) -> StreakOut:
    with session.begin() as c:
        return StreakOut(days=c.pairing.streak(session.user_id, pair_id))


@router.get("/attempts/to-review")
def to_review(session: CurrentSession) -> list[AttemptOut]:
    with session.begin() as c:
        return [AttemptOut.of(a) for a in c.pairing.to_review(session.user_id)]


@router.post("/attempts/{attempt_id}/correction")
def correct(attempt_id: UUID, body: CorrectionIn, session: CurrentSession) -> AttemptOut:
    with session.begin() as c:
        attempt = c.pairing.correct(session.user_id, attempt_id, body.corrected_text, body.comment)
    return AttemptOut.of(attempt)
