from datetime import timedelta
from uuid import uuid4

import pytest

from langex.identity.adapters.in_memory import (
    InMemoryAccountRepository,
    InMemoryRefreshTokenRepository,
)
from langex.identity.adapters.oidc import DevVerifier
from langex.identity.adapters.tokens import JwtAccessTokens
from langex.identity.application.service import IdentityService
from langex.identity.domain.account import ExternalIdentity, Provider
from langex.identity.domain.errors import AuthenticationError
from langex.identity.domain.refresh_token import RefreshToken
from tests.conftest import START, FakeClock


@pytest.fixture
def clock() -> FakeClock:
    return FakeClock()


@pytest.fixture
def service(clock: FakeClock) -> IdentityService:
    return IdentityService(
        accounts=InMemoryAccountRepository(),
        refresh_tokens=InMemoryRefreshTokenRepository(),
        access_tokens=JwtAccessTokens("k" * 40),
        verifiers={Provider.DEV: DevVerifier()},
        clock=clock,
        refresh_ttl=timedelta(days=30),
    )


def test_first_sign_in_opens_an_account_once(service: IdentityService) -> None:
    first = service.sign_in(Provider.DEV, "dev:amina")
    again = service.sign_in(Provider.DEV, "dev:amina")

    assert first.is_new_account
    assert not again.is_new_account
    assert again.account_id == first.account_id
    assert service.authenticate(first.access_token) == first.account_id
    assert service.providers == [Provider.DEV]


def test_disabled_provider_is_refused(service: IdentityService) -> None:
    with pytest.raises(AuthenticationError):
        service.sign_in(Provider.APPLE, "anything")


def test_refresh_rotates_the_token(service: IdentityService) -> None:
    signed_in = service.sign_in(Provider.DEV, "dev:amina")
    refreshed = service.refresh(signed_in.refresh_token)

    assert refreshed.refresh_token != signed_in.refresh_token
    assert refreshed.account_id == signed_in.account_id
    assert service.refresh(refreshed.refresh_token).account_id == signed_in.account_id


def test_reusing_a_refresh_token_revokes_the_whole_family(service: IdentityService) -> None:
    signed_in = service.sign_in(Provider.DEV, "dev:amina")
    stolen = signed_in.refresh_token
    current = service.refresh(stolen).refresh_token

    with pytest.raises(AuthenticationError) as error:
        service.refresh(stolen)  # the attacker (or the victim) replays the old token
    assert "reused" in error.value.reason
    with pytest.raises(AuthenticationError):
        service.refresh(current)  # the newest token in the family is dead too


def test_other_devices_keep_working_after_a_reuse(service: IdentityService) -> None:
    phone = service.sign_in(Provider.DEV, "dev:amina")
    tablet = service.sign_in(Provider.DEV, "dev:amina")
    service.refresh(phone.refresh_token)
    with pytest.raises(AuthenticationError):
        service.refresh(phone.refresh_token)

    assert service.refresh(tablet.refresh_token)


def test_refresh_token_expires(service: IdentityService, clock: FakeClock) -> None:
    signed_in = service.sign_in(Provider.DEV, "dev:amina")
    clock.advance(timedelta(days=30))
    with pytest.raises(AuthenticationError, match="Authentication failed"):
        service.refresh(signed_in.refresh_token)


def test_unknown_refresh_token(service: IdentityService) -> None:
    with pytest.raises(AuthenticationError):
        service.refresh("never-issued")


def test_sign_out_ends_the_session_and_is_idempotent(service: IdentityService) -> None:
    signed_in = service.sign_in(Provider.DEV, "dev:amina")
    service.sign_out(signed_in.refresh_token)
    service.sign_out(signed_in.refresh_token)
    service.sign_out("never-issued")
    with pytest.raises(AuthenticationError):
        service.refresh(signed_in.refresh_token)


def test_token_for_a_missing_account_is_rejected(clock: FakeClock) -> None:
    tokens = JwtAccessTokens("k" * 40)
    service = IdentityService(
        accounts=InMemoryAccountRepository(),
        refresh_tokens=InMemoryRefreshTokenRepository(),
        access_tokens=tokens,
        verifiers={},
        clock=clock,
    )
    with pytest.raises(AuthenticationError):
        service.authenticate(tokens.issue(uuid4(), START))


def test_domain_rules() -> None:
    with pytest.raises(ValueError, match="1-255"):
        ExternalIdentity(Provider.APPLE, "")
    record, _ = RefreshToken.issue(uuid4(), START, timedelta(days=1))
    assert record.revoked(START).revoked(START + timedelta(days=1)).revoked_at == START
    with pytest.raises(ValueError, match="expire"):
        RefreshToken.issue(record.account_id, START, timedelta(0))
