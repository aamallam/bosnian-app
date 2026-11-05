"""Configuration from environment variables only (12-factor).

Every variable starts with LANGEX_. Unsafe combinations (a weak secret,
dev sign-in or SQLite outside development) fail at start-up rather than
at the first request.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Annotated

from pydantic import Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

MIN_SECRET_LENGTH = 32


class Environment(StrEnum):
    DEVELOPMENT = "development"
    TEST = "test"
    STAGING = "staging"
    PRODUCTION = "production"

    @property
    def is_deployed(self) -> bool:
        return self in (Environment.STAGING, Environment.PRODUCTION)


def _split(value: object) -> object:
    if isinstance(value, str):
        return [part.strip() for part in value.split(",") if part.strip()]
    return value


CommaList = Annotated[list[str], NoDecode]
DEFAULT_DATABASE_URL = "sqlite+pysqlite:///./langex-dev.db"


def sqlalchemy_url(url: str) -> str:
    """Hosts such as Neon and Render hand out `postgres://` URLs; use psycopg 3."""
    for prefix in ("postgres://", "postgresql://"):
        if url.startswith(prefix):
            return "postgresql+psycopg://" + url.removeprefix(prefix)
    return url


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="LANGEX_", extra="ignore", frozen=True)

    env: Environment = Environment.DEVELOPMENT
    database_url: str = DEFAULT_DATABASE_URL
    jwt_secret: SecretStr = Field(min_length=MIN_SECRET_LENGTH)
    access_token_minutes: int = Field(default=15, ge=1, le=60)
    refresh_token_days: int = Field(default=30, ge=1, le=90)
    google_client_ids: CommaList = Field(default_factory=list)
    apple_client_ids: CommaList = Field(default_factory=list)
    allow_dev_sign_in: bool = False
    auth_rate_per_minute: int = Field(default=10, ge=1)
    api_rate_per_minute: int = Field(default=120, ge=1)
    max_body_bytes: int = Field(default=64 * 1024, ge=1024)
    log_level: str = "INFO"

    @model_validator(mode="before")
    @classmethod
    def _split_lists(cls, data: object) -> object:
        if isinstance(data, dict):
            for key in ("google_client_ids", "apple_client_ids"):
                if key in data:
                    data[key] = _split(data[key])
        return data

    @model_validator(mode="after")
    def _safe_for_environment(self) -> Settings:
        if self.env.is_deployed:
            if self.allow_dev_sign_in:
                raise ValueError("Dev sign-in must never be enabled in staging or production")
            if not self.database_url.startswith(("postgresql", "postgres")):
                raise ValueError("Staging and production need PostgreSQL")
        return self

    @property
    def sqlalchemy_url(self) -> str:
        return sqlalchemy_url(self.database_url)

    @property
    def docs_enabled(self) -> bool:
        return not self.env.is_deployed
