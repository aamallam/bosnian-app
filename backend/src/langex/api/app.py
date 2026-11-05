"""FastAPI application factory.

Run locally:   uvicorn langex.api.app:create_app --factory --reload
In the image:  see backend/Dockerfile (migrations run first, then uvicorn).
"""

from __future__ import annotations

import json
import logging
from collections.abc import Mapping
from typing import Any

from fastapi import FastAPI
from sqlalchemy import Engine, create_engine, event

from langex.api.dependencies import UnitOfWork
from langex.api.errors import install_error_handlers
from langex.api.middleware import (
    BodySizeLimitMiddleware,
    RequestContextMiddleware,
    SecurityHeadersMiddleware,
)
from langex.api.rate_limit import RateLimiter
from langex.api.routes import auth, learning, meta, pairing
from langex.bootstrap.container import (
    Infrastructure,
    assemble,
    infrastructure_from,
    sql_repositories,
)
from langex.bootstrap.settings import Settings
from langex.identity.application.ports import IdTokenVerifier
from langex.identity.domain.account import Provider
from langex.shared_kernel.clock import Clock

API_VERSION = "0.3.0"
_STANDARD_LOG_FIELDS = set(logging.makeLogRecord({}).__dict__) | {"message", "asctime"}


class JsonFormatter(logging.Formatter):
    """One JSON object per line, ready for the host's log viewer."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        payload.update({k: v for k, v in record.__dict__.items() if k not in _STANDARD_LOG_FIELDS})
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str)


def configure_logging(level: str) -> None:
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger("langex")
    root.handlers = [handler]
    root.setLevel(level)
    root.propagate = False


def create_engine_for(settings: Settings) -> Engine:
    url = settings.sqlalchemy_url
    if url.startswith("sqlite"):
        engine = create_engine(url)

        @event.listens_for(engine, "connect")
        def _sqlite_foreign_keys(dbapi_connection: Any, _record: Any) -> None:
            dbapi_connection.execute("PRAGMA foreign_keys=ON")

        return engine
    # Small pool for the free tier; pre-ping survives the database scaling to zero.
    return create_engine(url, pool_size=5, max_overflow=5, pool_pre_ping=True, pool_recycle=300)


def create_app(
    settings: Settings | None = None,
    *,
    engine: Engine | None = None,
    clock: Clock | None = None,
    verifiers: Mapping[Provider, IdTokenVerifier] | None = None,
) -> FastAPI:
    settings = settings or Settings()  # type: ignore[call-arg]  # values come from the environment
    configure_logging(settings.log_level)
    engine = engine or create_engine_for(settings)
    infra: Infrastructure = infrastructure_from(settings, clock=clock, verifiers=verifiers)

    app = FastAPI(
        title="Langex API",
        version=API_VERSION,
        docs_url="/docs" if settings.docs_enabled else None,
        redoc_url=None,
        openapi_url="/openapi.json" if settings.docs_enabled else None,
    )
    app.state.uow = UnitOfWork(
        engine, lambda connection: assemble(sql_repositories(connection), infra)
    )
    app.state.rate_limiter = RateLimiter()
    app.state.rate_limits = {
        "auth": settings.auth_rate_per_minute,
        "api": settings.api_rate_per_minute,
    }
    app.state.access_token_seconds = settings.access_token_minutes * 60

    install_error_handlers(app)
    app.include_router(meta.router)
    for router in (auth.router, pairing.router, learning.router):
        app.include_router(router, prefix="/v1")

    # Outermost first: request IDs wrap everything, then headers, then size limit.
    app.add_middleware(BodySizeLimitMiddleware, max_bytes=settings.max_body_bytes)
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(RequestContextMiddleware)
    return app
