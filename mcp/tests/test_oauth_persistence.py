"""OAuth clients and tokens survive a provider restart when a state file is set."""

import stat
from pathlib import Path

from mcp.shared.auth import OAuthClientInformationFull

from app.oauth import SinglePasswordOAuthProvider


def _provider(state_file: Path) -> SinglePasswordOAuthProvider:
    return SinglePasswordOAuthProvider(base_url="https://example.test", state_file=state_file)


async def test_clients_and_tokens_survive_restart(tmp_path: Path) -> None:
    state_file = tmp_path / "oauth_state.json"
    first = _provider(state_file)
    client = OAuthClientInformationFull(client_id="c1", redirect_uris=["https://claude.ai/cb"])
    await first.register_client(client)
    issued = first._issue_tokens("c1", [], "https://example.test/mcp")

    second = _provider(state_file)
    assert await second.get_client("c1") is not None
    access = await second.load_access_token(issued.access_token)
    assert access is not None
    assert access.resource == "https://example.test/mcp"
    refresh = await second.load_refresh_token(client, issued.refresh_token)
    assert refresh is not None
    assert stat.S_IMODE(state_file.stat().st_mode) == 0o600


async def test_revoked_token_stays_revoked_after_restart(tmp_path: Path) -> None:
    state_file = tmp_path / "oauth_state.json"
    first = _provider(state_file)
    issued = first._issue_tokens("c1", [], None)
    first._revoke(access=issued.access_token)

    assert await _provider(state_file).load_access_token(issued.access_token) is None


async def test_corrupt_state_file_starts_empty(tmp_path: Path) -> None:
    state_file = tmp_path / "oauth_state.json"
    state_file.write_text("not json")

    provider = _provider(state_file)
    assert provider.clients == {}
    assert provider.access_tokens == {}
