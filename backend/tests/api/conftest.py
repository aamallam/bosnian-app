from __future__ import annotations

from collections.abc import Callable, Iterator
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine

from langex.api.app import create_app
from langex.bootstrap.settings import Environment, Settings
from tests.conftest import FakeClock


def settings_for(**changes: Any) -> Settings:
    values: dict[str, Any] = {
        "env": Environment.TEST,
        "jwt_secret": "t" * 40,
        "allow_dev_sign_in": True,
        "auth_rate_per_minute": 1000,
        "api_rate_per_minute": 1000,
    }
    values.update(changes)
    return Settings(**values)


@pytest.fixture
def clock() -> FakeClock:
    return FakeClock()


@pytest.fixture
def make_client(engine: Engine, clock: FakeClock) -> Iterator[Callable[..., TestClient]]:
    clients: list[TestClient] = []

    def make(**changes: Any) -> TestClient:
        client = TestClient(
            create_app(settings_for(**changes), engine=engine, clock=clock),
            raise_server_exceptions=False,
        )
        clients.append(client)
        return client

    yield make
    for client in clients:
        client.close()


@pytest.fixture
def client(make_client: Callable[..., TestClient]) -> TestClient:
    return make_client()


def sign_in(client: TestClient, name: str) -> dict[str, Any]:
    response = client.post("/v1/auth/sign-in", json={"provider": "dev", "id_token": f"dev:{name}"})
    assert response.status_code == 200, response.text
    body: dict[str, Any] = response.json()
    return body


def auth(tokens: dict[str, Any]) -> dict[str, str]:
    return {"Authorization": f"Bearer {tokens['access_token']}"}
