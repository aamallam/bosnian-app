"""OWASP API Top 10 style checks: authentication, input handling, limits,
headers and information leakage."""

from __future__ import annotations

from collections.abc import Callable
from datetime import timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine

from langex.api.app import create_app
from langex.api.rate_limit import RateLimiter
from tests.api.conftest import auth, settings_for, sign_in
from tests.conftest import FakeClock

PROTECTED = [
    ("get", "/v1/me"),
    ("get", "/v1/pairs"),
    ("post", "/v1/invitations"),
    ("get", "/v1/reviews/session"),
    ("get", "/v1/attempts/to-review"),
]


@pytest.mark.parametrize(("method", "path"), PROTECTED)
@pytest.mark.parametrize(
    "headers",
    [{}, {"Authorization": "Bearer garbage"}, {"Authorization": "Basic dXNlcjpwYXNz"}],
)
def test_protected_routes_need_a_valid_token(
    client: TestClient, method: str, path: str, headers: dict[str, str]
) -> None:
    response = client.request(method, path, headers=headers, json={})
    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"
    assert response.headers["content-type"] == "application/problem+json"
    assert response.json()["title"] == "Authentication failed"


def test_access_token_expires(client: TestClient, clock: FakeClock) -> None:
    headers = auth(sign_in(client, "amina"))
    assert client.get("/v1/me", headers=headers).status_code == 200
    clock.advance(timedelta(minutes=16))
    assert client.get("/v1/me", headers=headers).status_code == 401


def test_refresh_rotation_and_reuse_detection_over_http(client: TestClient) -> None:
    first = sign_in(client, "amina")
    rotated = client.post("/v1/auth/refresh", json={"refresh_token": first["refresh_token"]})
    assert rotated.status_code == 200
    assert rotated.json()["expires_in"] == 15 * 60

    replay = client.post("/v1/auth/refresh", json={"refresh_token": first["refresh_token"]})
    assert replay.status_code == 401
    # The revocation was committed although the request failed.
    newest = client.post(
        "/v1/auth/refresh", json={"refresh_token": rotated.json()["refresh_token"]}
    )
    assert newest.status_code == 401


def test_sign_out(client: TestClient) -> None:
    tokens = sign_in(client, "amina")
    out = client.post("/v1/auth/sign-out", json={"refresh_token": tokens["refresh_token"]})
    assert out.status_code == 204
    again = client.post("/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert again.status_code == 401


def test_disabled_provider_is_refused(make_client: Callable[..., TestClient]) -> None:
    client = make_client(allow_dev_sign_in=False)
    response = client.post("/v1/auth/sign-in", json={"provider": "dev", "id_token": "dev:x"})
    assert response.status_code == 401


def test_unknown_fields_and_oversized_values_are_rejected(client: TestClient) -> None:
    headers = auth(sign_in(client, "amina"))
    extra = client.post(
        "/v1/invitations",
        json={"teaches": "ar", "learns": "bs", "is_admin": True},  # mass assignment
        headers=headers,
    )
    assert extra.status_code == 422
    secret = "x" * 700
    long = client.post(
        "/v1/pairs/00000000-0000-0000-0000-000000000000/contributions",
        json={"text": secret},
        headers=headers,
    )
    assert long.status_code == 422
    assert secret not in long.text  # input is never echoed back
    bad_code = client.post(
        "/v1/invitations", json={"teaches": "AR!", "learns": "bs"}, headers=headers
    )
    assert bad_code.status_code == 422


def test_large_bodies_are_rejected_early(client: TestClient) -> None:
    response = client.post(
        "/v1/auth/sign-in",
        content=b"{" + b" " * (70 * 1024) + b"}",
        headers={"content-type": "application/json"},
    )
    assert response.status_code == 413


def test_security_headers(client: TestClient) -> None:
    response = client.get("/healthz")
    assert response.json() == {"status": "ok"}
    headers = response.headers
    assert headers["x-content-type-options"] == "nosniff"
    assert headers["x-frame-options"] == "DENY"
    assert headers["cache-control"] == "no-store"
    assert "max-age" in headers["strict-transport-security"]
    assert headers["content-security-policy"].startswith("default-src 'none'")
    assert "server" not in headers
    assert len(headers["x-request-id"]) == 32


def test_auth_routes_are_rate_limited(make_client: Callable[..., TestClient]) -> None:
    client = make_client(auth_rate_per_minute=3)
    codes = [
        client.post("/v1/auth/refresh", json={"refresh_token": "x"}).status_code for _ in range(4)
    ]
    assert codes == [401, 401, 401, 429]


def test_docs_are_hidden_when_deployed(engine: Engine, clock: FakeClock) -> None:
    settings = settings_for(
        env="staging", allow_dev_sign_in=False, database_url="postgresql://u@h/d"
    )
    with TestClient(create_app(settings, engine=engine, clock=clock)) as client:
        assert client.get("/docs").status_code == 404
        assert client.get("/openapi.json").status_code == 404


def test_docs_are_available_in_development(client: TestClient) -> None:
    schema = client.get("/openapi.json").json()
    assert "/v1/pairs/{pair_id}/contributions" in schema["paths"]
    assert client.get("/docs").status_code == 200


def test_readiness_checks_the_database(client: TestClient) -> None:
    assert client.get("/readyz").json() == {"status": "ready"}


def test_unexpected_errors_reveal_nothing(client: TestClient) -> None:
    def boom() -> None:
        raise RuntimeError("database password is hunter2")

    client.app.add_api_route("/boom", boom)  # type: ignore[attr-defined]
    response = client.get("/boom")
    assert response.status_code == 500
    assert "hunter2" not in response.text
    assert response.json()["request_id"]


class TickingClock:
    def __init__(self) -> None:
        self.now = 0.0

    def __call__(self) -> float:
        return self.now


def test_rate_limiter_window_and_eviction() -> None:
    clock = TickingClock()
    limiter = RateLimiter(clock=clock, max_keys=4)
    assert limiter.hit("a", 2) is None
    assert limiter.hit("a", 2) is None
    assert limiter.hit("a", 2) == pytest.approx(60.0)
    clock.now = 61
    assert limiter.hit("a", 2) is None

    for key in "bcdefgh":
        assert limiter.hit(key, 1) is None  # old keys are evicted, memory stays bounded
    assert len(limiter._hits) <= 4
