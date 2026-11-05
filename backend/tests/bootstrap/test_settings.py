import pytest
from pydantic import ValidationError

from langex.bootstrap.container import verifiers_from
from langex.bootstrap.settings import Environment, Settings, sqlalchemy_url
from langex.identity.domain.account import Provider

SECRET = "z" * 40
PG = "postgresql://u:p@db.example/langex"


def test_reads_environment_variables(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LANGEX_JWT_SECRET", SECRET)
    monkeypatch.setenv("LANGEX_ENV", "staging")
    monkeypatch.setenv("LANGEX_DATABASE_URL", PG)
    monkeypatch.setenv("LANGEX_GOOGLE_CLIENT_IDS", "a.apps.googleusercontent.com, b ")
    settings = Settings()  # type: ignore[call-arg]

    assert settings.env is Environment.STAGING
    assert settings.google_client_ids == ["a.apps.googleusercontent.com", "b"]
    assert settings.sqlalchemy_url.startswith("postgresql+psycopg://")
    assert not settings.docs_enabled
    assert SECRET not in repr(settings)  # secrets never end up in logs


def test_weak_secret_is_refused() -> None:
    with pytest.raises(ValidationError):
        Settings(jwt_secret="too-short")  # type: ignore[arg-type]


@pytest.mark.parametrize(
    "changes",
    [
        {"allow_dev_sign_in": True, "database_url": PG},
        {"database_url": "sqlite+pysqlite:///x.db"},
    ],
)
def test_unsafe_settings_are_refused_when_deployed(changes: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        Settings(jwt_secret=SECRET, env=Environment.PRODUCTION, **changes)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    ("url", "expected"),
    [
        ("postgres://u@h/d", "postgresql+psycopg://u@h/d"),
        ("postgresql://u@h/d", "postgresql+psycopg://u@h/d"),
        ("postgresql+psycopg://u@h/d", "postgresql+psycopg://u@h/d"),
        ("sqlite+pysqlite://", "sqlite+pysqlite://"),
    ],
)
def test_database_url_uses_psycopg(url: str, expected: str) -> None:
    assert sqlalchemy_url(url) == expected


def test_only_configured_providers_are_enabled() -> None:
    settings = Settings(
        jwt_secret=SECRET,  # type: ignore[arg-type]
        apple_client_ids=["com.example.langex"],
        google_client_ids=["g.apps.googleusercontent.com"],
    )
    assert set(verifiers_from(settings)) == {Provider.APPLE, Provider.GOOGLE}
    dev = Settings(jwt_secret=SECRET, allow_dev_sign_in=True)  # type: ignore[arg-type]
    assert set(verifiers_from(dev)) == {Provider.DEV}
