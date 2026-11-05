"""Per-request unit of work and authentication."""

from __future__ import annotations

from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Annotated
from uuid import UUID

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import Connection, Engine

from langex.bootstrap.container import Container
from langex.identity.domain.errors import AuthenticationError

ContainerFactory = Callable[[Connection], Container]

_bearer = HTTPBearer(auto_error=False)


@dataclass(frozen=True, slots=True)
class UnitOfWork:
    """One database transaction per request: the use case and the event
    handlers it triggers commit together, or roll back together."""

    engine: Engine
    factory: ContainerFactory

    @contextmanager
    def begin(self, *, commit_on: tuple[type[Exception], ...] = ()) -> Iterator[Container]:
        """`commit_on` lists errors whose side effects must still be saved,
        e.g. revoking a token family when a stolen refresh token is replayed."""
        with self.engine.connect() as connection:
            transaction = connection.begin()
            try:
                yield self.factory(connection)
            except commit_on:
                transaction.commit()
                raise
            except BaseException:
                transaction.rollback()
                raise
            transaction.commit()


def get_uow(request: Request) -> UnitOfWork:
    uow: UnitOfWork = request.app.state.uow
    return uow


def bearer_token(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> str:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise AuthenticationError("missing bearer token")
    return credentials.credentials


@dataclass(frozen=True, slots=True)
class Session:
    """An authenticated request: who is acting, and how to run use cases."""

    user_id: UUID
    uow: UnitOfWork

    @contextmanager
    def begin(self) -> Iterator[Container]:
        with self.uow.begin() as container:
            yield container


def current_session(
    uow: Annotated[UnitOfWork, Depends(get_uow)],
    token: Annotated[str, Depends(bearer_token)],
) -> Session:
    with uow.begin() as container:
        user_id = container.identity.authenticate(token)
    return Session(user_id=user_id, uow=uow)


Uow = Annotated[UnitOfWork, Depends(get_uow)]
CurrentSession = Annotated[Session, Depends(current_session)]
