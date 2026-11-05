"""Migrations must build exactly the schema the code expects, and undo cleanly."""

from __future__ import annotations

from pathlib import Path

from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.migration import MigrationContext
from sqlalchemy import Engine, inspect

from langex.bootstrap.database import ALL_METADATA
from tests.conftest import make_engine

BACKEND = Path(__file__).resolve().parents[2]


def _config(engine: Engine) -> Config:
    config = Config(str(BACKEND / "alembic.ini"))
    config.attributes["configure_logger"] = False
    return config


def _clean(engine: Engine) -> None:
    with engine.begin() as connection:
        for metadata in reversed(ALL_METADATA):
            metadata.drop_all(connection)
        connection.exec_driver_sql("DROP TABLE IF EXISTS alembic_version")


def test_migrations_match_the_models_and_downgrade() -> None:
    engine = make_engine()
    _clean(engine)
    config = _config(engine)
    try:
        with engine.begin() as connection:
            config.attributes["connection"] = connection
            command.upgrade(config, "head")
            diff = compare_metadata(
                MigrationContext.configure(connection, opts={"compare_type": True}),
                list(ALL_METADATA),
            )
        assert diff == [], f"Models and migrations differ; add a migration: {diff}"

        with engine.begin() as connection:
            config.attributes["connection"] = connection
            command.downgrade(config, "base")
            assert inspect(connection).get_table_names() == ["alembic_version"]
    finally:
        _clean(engine)
        engine.dispose()
