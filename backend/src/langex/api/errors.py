"""Domain errors to RFC 9457 problem responses.

Not-found and not-yours share one response (no IDOR oracle). Unexpected
errors return a generic 500 with the request ID only; details go to logs.
"""

from __future__ import annotations

import logging

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from langex.identity.domain.errors import AuthenticationError
from langex.learning.application.reviews import CardNotFoundError
from langex.pairing.domain.errors import (
    AttemptNotFoundError,
    DailyLimitReachedError,
    InvitationError,
    PairingError,
    PairNotFoundError,
)

log = logging.getLogger("langex.api")
PROBLEM = "application/problem+json"


def problem(
    request: Request,
    status_code: int,
    title: str,
    detail: str | None = None,
    headers: dict[str, str] | None = None,
    errors: list[dict[str, object]] | None = None,
) -> JSONResponse:
    body: dict[str, object] = {"title": title, "status": status_code}
    if detail:
        body["detail"] = detail
    if errors:
        body["errors"] = errors
    request_id = getattr(request.state, "request_id", None)
    if request_id:
        body["request_id"] = request_id
    return JSONResponse(body, status_code=status_code, headers=headers, media_type=PROBLEM)


def install_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(AuthenticationError)
    async def _auth(request: Request, error: AuthenticationError) -> JSONResponse:
        log.info("authentication failed", extra={"reason": error.reason})
        return problem(
            request,
            status.HTTP_401_UNAUTHORIZED,
            "Authentication failed",
            headers={"WWW-Authenticate": "Bearer"},
        )

    @app.exception_handler(PairNotFoundError)
    @app.exception_handler(AttemptNotFoundError)
    @app.exception_handler(CardNotFoundError)
    async def _not_found(request: Request, error: Exception) -> JSONResponse:
        return problem(request, status.HTTP_404_NOT_FOUND, "Not found")

    @app.exception_handler(DailyLimitReachedError)
    async def _quota(request: Request, error: DailyLimitReachedError) -> JSONResponse:
        return problem(
            request, status.HTTP_429_TOO_MANY_REQUESTS, "Daily limit reached", str(error)
        )

    @app.exception_handler(InvitationError)
    async def _invitation(request: Request, error: InvitationError) -> JSONResponse:
        return problem(request, status.HTTP_400_BAD_REQUEST, "Invitation not usable", str(error))

    @app.exception_handler(PairingError)
    async def _conflict(request: Request, error: PairingError) -> JSONResponse:
        return problem(request, status.HTTP_409_CONFLICT, "Conflict", str(error))

    @app.exception_handler(ValueError)
    async def _domain_rule(request: Request, error: ValueError) -> JSONResponse:
        # Domain value objects raise ValueError with user-safe messages.
        return problem(request, status.HTTP_422_UNPROCESSABLE_CONTENT, "Invalid input", str(error))

    @app.exception_handler(RequestValidationError)
    async def _validation(request: Request, error: RequestValidationError) -> JSONResponse:
        errors = [
            {"location": list(e.get("loc", ())), "message": e.get("msg", "")}
            for e in error.errors()
        ]  # input values are deliberately not echoed back
        return problem(
            request, status.HTTP_422_UNPROCESSABLE_CONTENT, "Invalid input", errors=errors
        )

    @app.exception_handler(StarletteHTTPException)
    async def _http(request: Request, error: StarletteHTTPException) -> JSONResponse:
        return problem(
            request,
            error.status_code,
            str(error.detail),
            headers=dict(error.headers) if error.headers else None,
        )

    @app.exception_handler(Exception)
    async def _unexpected(request: Request, error: Exception) -> JSONResponse:
        log.exception("unhandled error")
        return problem(request, status.HTTP_500_INTERNAL_SERVER_ERROR, "Internal error")
