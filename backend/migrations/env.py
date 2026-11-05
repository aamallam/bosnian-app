"""Alembic environment: one migration history for every context's tables."""

from __future__ import annotations

import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy import create_engine, pool

from langex.bootstrap.database import ALL_METADATA
from langex.bootstrap.settings import DEFAULT_DATABASE_URL, sqlalchemy_url
from langex.platform.sql import UtcDateTime

config = context.config
if config.config_file_name is not None and config.attributes.get("configure_logger", True):
    fileConfig(config.config_file_name)

target_metadata = list(ALL_METADATA)


def _url() -> str:
    url = config.attributes.get("url") or os.environ.get(
        "LANGEX_DATABASE_URL", DEFAULT_DATABASE_URL
    )
    return sqlalchemy_url(str(url))


def run_migrations_offline() -> None:
    context.configure(
        url=_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        render_as_batch=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connection = config.attributes.get("connection")
    if connection is not None:
        _run(connection)
        return
    engine = create_engine(_url(), poolclass=pool.NullPool)
    with engine.connect() as new_connection:
        _run(new_connection)


def _render_item(type_: str, obj: object, autogen_context: object) -> str | bool:
    """Write app-only column types as plain SQLAlchemy types, so migrations
    never import application code (which may change after they are written)."""
    if type_ == "type" and isinstance(obj, UtcDateTime):
        return "sa.DateTime(timezone=True)"
    return False


def _run(connection: object) -> None:
    context.configure(
        connection=connection,  # type: ignore[arg-type]
        target_metadata=target_metadata,
        render_as_batch=True,  # lets the same migrations run on SQLite in dev
        compare_type=True,
        render_item=_render_item,
    )
    with context.begin_transaction():
        context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
