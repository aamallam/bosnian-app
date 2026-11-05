"""Shared fixtures.

SQL tests run on in-memory SQLite by default (fast, no setup). Set
TEST_DATABASE_URL to run the same tests on PostgreSQL, as CI does.
"""

from __future__ import annotations

import os
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import Connection, Engine, create_engine, event
from sqlalchemy.pool import StaticPool

from langex.bootstrap.database import ALL_METADATA, create_all
from langex.bootstrap.settings import sqlalchemy_url

START = datetime(2026, 11, 4, 9, 0, tzinfo=UTC)


class FakeClock:
    def __init__(self, now: datetime = START) -> None:
        self.current = now

    def now(self) -> datetime:
        return self.current

    def advance(self, delta: timedelta) -> None:
        self.current += delta


def _sqlite_engine() -> Engine:
    engine = create_engine(
        "sqlite+pysqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,  # one shared in-memory database for the test
    )

    @event.listens_for(engine, "connect")
    def _foreign_keys(dbapi_connection: object, _record: object) -> None:
        dbapi_connection.execute("PRAGMA foreign_keys=ON")  # type: ignore[attr-defined]

    return engine


def make_engine() -> Engine:
    url = os.environ.get("TEST_DATABASE_URL")
    engine = create_engine(sqlalchemy_url(url)) if url else _sqlite_engine()
    with engine.begin() as connection:
        for metadata in reversed(ALL_METADATA):
            metadata.drop_all(connection)
        create_all(connection)
    return engine


@pytest.fixture
def engine() -> Iterator[Engine]:
    engine = make_engine()
    yield engine
    engine.dispose()


@pytest.fixture
def connection(engine: Engine) -> Iterator[Connection]:
    """A connection inside a transaction that is rolled back afterwards."""
    with engine.connect() as connection:
        transaction = connection.begin()
        yield connection
        transaction.rollback()
