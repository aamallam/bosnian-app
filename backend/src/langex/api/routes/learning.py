from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends

from langex.api.dependencies import CurrentSession
from langex.api.rate_limit import RateLimit
from langex.api.schemas import CardOut, ReviewIn
from langex.learning.domain.card import Rating

router = APIRouter(tags=["learning"], dependencies=[Depends(RateLimit("api"))])


@router.get("/reviews/session")
def review_session(session: CurrentSession) -> list[CardOut]:
    """Due cards first, then today's new cards."""
    with session.begin() as c:
        return [CardOut.of(card) for card in c.learning.session(session.user_id)]


@router.post("/reviews/{card_id}")
def review(card_id: UUID, body: ReviewIn, session: CurrentSession) -> CardOut:
    with session.begin() as c:
        card = c.learning.submit(session.user_id, card_id, Rating(body.rating), body.duration_ms)
    return CardOut.of(card)
