"""Every context's tables, gathered for Alembic and for tests."""

from __future__ import annotations

from sqlalchemy import Connection, MetaData

from langex.identity.adapters.sql import metadata as identity_metadata
from langex.learning.adapters.sql import metadata as learning_metadata
from langex.pairing.adapters.sql import metadata as pairing_metadata

ALL_METADATA: tuple[MetaData, ...] = (identity_metadata, pairing_metadata, learning_metadata)


def create_all(connection: Connection) -> None:
    """Fast schema set-up for tests. Real databases use Alembic migrations."""
    for metadata in ALL_METADATA:
        metadata.create_all(connection)
