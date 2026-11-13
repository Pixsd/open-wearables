"""Behaviour of the OAuth provider's token lifecycle, login and registration."""

import time
from pathlib import Path

import pytest
from mcp.shared.auth import OAuthClientInformationFull
from pydantic import SecretStr
from starlette.requests import Request

from app.auth import SharedSecretVerifier
from app.config import settings
from app.oauth import UNUSED_CLIENT_EXPIRY_SECONDS, SinglePasswordOAuthProvider


def _provider(state_file: Path | None = None) -> SinglePasswordOAuthProvider:
    return SinglePasswordOAuthProvider(base_url="https://example.test", state_file=state_file)


def _client(client_id: str = "c1") -> OAuthClientInformationFull:
    return OAuthClientInformationFull(client_id=client_id, redirect_uris=["https://claude.ai/cb"])


async def test_refresh_token_outlives_expired_access_token(tmp_path: Path) -> None:
    state_file = tmp_path / "oauth_state.json"
    provider = _provider(state_file)
    client = _client()
    await provider.register_client(client)
    issued = provider._issue_tokens("c1", [], None)
    provider.access_tokens[issued.access_token].expires_at = 1  # long past

    assert await provider.load_access_token(issued.access_token) is None

    for p in (provider, _provider(state_file)):
        refresh = await p.load_refresh_token(client, issued.refresh_token)
        assert refresh is not None
    renewed = await provider.exchange_refresh_token(client, refresh, [])
    assert await provider.load_access_token(renewed.access_token) is not None


async def test_gc_keeps_refresh_token_of_expired_access_token() -> None:
    provider = _provider()
    issued = provider._issue_tokens("c1", [], None)
    provider.access_tokens[issued.access_token].expires_at = 1

    provider._gc()

    assert issued.access_token not in provider.access_tokens
    assert issued.refresh_token in provider.refresh_tokens


async def test_bearer_verifier_handles_non_ascii_tokens(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "mcp_bearer_token", SecretStr("sécret-tøken"))
    verifier = SharedSecretVerifier()

    assert await verifier.verify_token("sécret-tøken") is not None
    assert await verifier.verify_token("wrong-é") is None


def _request(headers: dict[str, str], peer: str = "172.18.0.1") -> Request:
    scope = {
        "type": "http",
        "headers": [(k.lower().encode(), v.encode()) for k, v in headers.items()],
        "client": (peer, 1234),
    }
    return Request(scope)


def test_client_ip_is_the_socket_peer_by_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "mcp_client_ip_header", "")

    assert SinglePasswordOAuthProvider._client_ip(_request({"X-Forwarded-For": "9.9.9.9"})) == "172.18.0.1"


def test_client_ip_uses_the_configured_header(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "mcp_client_ip_header", "X-Forwarded-For")

    assert SinglePasswordOAuthProvider._client_ip(_request({"X-Forwarded-For": "6.6.6.6, 1.2.3.4"})) == "1.2.3.4"
    assert SinglePasswordOAuthProvider._client_ip(_request({})) == "172.18.0.1"


async def test_unused_clients_expire_so_registration_cannot_be_filled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("app.oauth.MAX_REGISTERED_CLIENTS", 2)
    provider = _provider()
    stale = int(time.time()) - 2 * UNUSED_CLIENT_EXPIRY_SECONDS
    for client_id in ("squat-1", "squat-2"):
        client = _client(client_id)
        client.client_id_issued_at = stale
        await provider.register_client(client)

    await provider.register_client(_client("claude"))

    assert set(provider.clients) == {"claude"}


async def test_client_holding_a_token_is_kept() -> None:
    provider = _provider()
    client = _client("c1")
    client.client_id_issued_at = int(time.time()) - 2 * UNUSED_CLIENT_EXPIRY_SECONDS
    await provider.register_client(client)
    provider._issue_tokens("c1", [], None)

    provider._gc()

    assert "c1" in provider.clients
