from __future__ import annotations

from fastapi import APIRouter, Depends, Request, status

from langex.api.dependencies import CurrentSession, Uow
from langex.api.rate_limit import RateLimit
from langex.api.schemas import Me, RefreshRequest, SignInRequest, TokenResponse
from langex.identity.application.service import TokenPair
from langex.identity.domain.errors import AuthenticationError

router = APIRouter(tags=["auth"], dependencies=[Depends(RateLimit("auth"))])


def _response(request: Request, tokens: TokenPair) -> TokenResponse:
    return TokenResponse(
        access_token=tokens.access_token,
        refresh_token=tokens.refresh_token,
        expires_in=request.app.state.access_token_seconds,
        account_id=tokens.account_id,
        is_new_account=tokens.is_new_account,
    )


@router.post("/auth/sign-in")
def sign_in(body: SignInRequest, uow: Uow, request: Request) -> TokenResponse:
    """Exchange an Apple or Google ID token for our own tokens."""
    with uow.begin() as c:
        tokens = c.identity.sign_in(body.provider, body.id_token, body.nonce)
    return _response(request, tokens)


@router.post("/auth/refresh")
def refresh(body: RefreshRequest, uow: Uow, request: Request) -> TokenResponse:
    """Rotate the refresh token. Reusing an old one signs the device out."""
    with uow.begin(commit_on=(AuthenticationError,)) as c:
        tokens = c.identity.refresh(body.refresh_token)
    return _response(request, tokens)


@router.post("/auth/sign-out", status_code=status.HTTP_204_NO_CONTENT)
def sign_out(body: RefreshRequest, uow: Uow) -> None:
    with uow.begin() as c:
        c.identity.sign_out(body.refresh_token)


@router.get("/me")
def me(session: CurrentSession) -> Me:
    return Me(id=session.user_id)
