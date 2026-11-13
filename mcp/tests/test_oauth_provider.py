"""Behaviour of the OAuth provider's token lifecycle, login and registration."""

from pathlib import Path

import pytest
from mcp.shared.auth import OAuthClientInformationFull
from pydantic import SecretStr

from app.auth import SharedSecretVerifier
from app.config import settings
from app.oauth import SinglePasswordOAuthProvider


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
