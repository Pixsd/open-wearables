"""Self-contained OAuth 2.1 authorization server, gated by a single password.

State (clients, codes, tokens) is kept in memory; a restart just means
connected clients need to reauthorize.
"""

import hmac
import html
import secrets
import time
from dataclasses import dataclass

from fastmcp.server.auth.auth import OAuthProvider
from fastmcp.utilities.ui import INFO_BOX_STYLES, create_page, create_secure_html_response
from mcp.server.auth.provider import (
    AccessToken,
    AuthorizationCode,
    AuthorizationParams,
    RefreshToken,
    TokenError,
    construct_redirect_uri,
)
from mcp.shared.auth import OAuthClientInformationFull, OAuthToken
from starlette.requests import Request
from starlette.responses import HTMLResponse, RedirectResponse, Response
from starlette.routing import Route

from app.config import settings

AUTH_CODE_EXPIRY_SECONDS = 5 * 60
PENDING_AUTH_EXPIRY_SECONDS = 10 * 60
ACCESS_TOKEN_EXPIRY_SECONDS = 30 * 24 * 60 * 60


@dataclass
class _PendingAuthorization:
    client: OAuthClientInformationFull
    params: AuthorizationParams
    expires_at: float


class SinglePasswordOAuthProvider(OAuthProvider):
    """OAuth authorization server backed by one shared password.

    Doesn't reuse fastmcp's InMemoryOAuthProvider: that one is documented as a
    testing double, and it doesn't track the resource/audience restriction
    (see _issue_tokens below) that this server needs to enforce.
    """

    def __init__(self, **kwargs: object) -> None:
        super().__init__(**kwargs)
        self.clients: dict[str, OAuthClientInformationFull] = {}
        self.auth_codes: dict[str, AuthorizationCode] = {}
        self.access_tokens: dict[str, AccessToken] = {}
        self.refresh_tokens: dict[str, RefreshToken] = {}
        self._access_to_refresh: dict[str, str] = {}
        self._refresh_to_access: dict[str, str] = {}
        self._pending: dict[str, _PendingAuthorization] = {}

    # --- Dynamic client registration (RFC 7591) ---
    async def get_client(self, client_id: str) -> OAuthClientInformationFull | None:
        return self.clients.get(client_id)

    async def register_client(self, client_info: OAuthClientInformationFull) -> None:
        if client_info.client_id is None:
            raise ValueError("client_id is required for client registration")
        self._gc()
        self.clients[client_info.client_id] = client_info

    # --- Authorization: hand off to our own login page ---
    async def authorize(self, client: OAuthClientInformationFull, params: AuthorizationParams) -> str:
        self._gc()
        txn = secrets.token_urlsafe(24)
        self._pending[txn] = _PendingAuthorization(
            client=client,
            params=params,
            expires_at=time.time() + PENDING_AUTH_EXPIRY_SECONDS,
        )
        base = str(self.base_url).rstrip("/")
        return f"{base}/login?txn={txn}"

    def _gc(self) -> None:
        """Sweep expired pending authorizations and access tokens.

        Bounds memory growth for a long-running, unattended server - clients
        and refresh tokens have no expiry by design (a personal deployment is
        expected to stay connected), so those are only removed via explicit
        revocation or rotation.
        """
        now = time.time()
        for txn in [k for k, v in self._pending.items() if v.expires_at < now]:
            del self._pending[txn]
        for token, access in list(self.access_tokens.items()):
            if access.expires_at is not None and access.expires_at < now:
                self._revoke(access=token)

    def _render_login(
        self,
        txn: str,
        client: OAuthClientInformationFull,
        redirect_uri: str,
        error: str | None = None,
    ) -> str:
        error_box = f'<div class="info-box error"><p>{html.escape(error)}</p></div>' if error else ""
        client_name = html.escape(client.client_name or client.client_id or "An application")
        content = f"""
            <div class="container">
                <h1>Sign in to Open Wearables</h1>
                <p><strong>{client_name}</strong> wants to access your wearable health data.
                   It will be redirected to <code>{html.escape(redirect_uri)}</code> once you sign in.</p>
                {error_box}
                <form method="post" action="/login">
                    <input type="hidden" name="txn" value="{html.escape(txn)}">
                    <input type="password" name="password" placeholder="Password" autofocus required
                           style="width:100%;padding:.6rem;margin:1rem 0;border:1px solid #e5e7eb;
                                  border-radius:.5rem;box-sizing:border-box;">
                    <button type="submit"
                            style="width:100%;padding:.6rem;border:0;border-radius:.5rem;
                                   background:#0a0a0a;color:#fff;font-weight:600;cursor:pointer;">
                        Authorize
                    </button>
                </form>
            </div>
        """
        return create_page(content=content, title="Sign in", additional_styles=INFO_BOX_STYLES)

    async def _handle_login_get(self, request: Request) -> HTMLResponse:
        txn = request.query_params.get("txn", "")
        pending = self._pending.get(txn)
        if pending is None:
            return create_secure_html_response(
                create_page(
                    content='<div class="container"><h1>Authorization request expired</h1>'
                    "<p>Please reconnect from your MCP client.</p></div>",
                    title="Expired",
                ),
                status_code=400,
            )
        error = request.query_params.get("error")
        login_page = self._render_login(txn, pending.client, str(pending.params.redirect_uri), error)
        return create_secure_html_response(login_page)

    async def _handle_login_post(self, request: Request) -> Response:
        form = await request.form()
        txn = str(form.get("txn", ""))
        password = str(form.get("password", ""))
        pending = self._pending.get(txn)
        if pending is None or pending.expires_at < time.time():
            return create_secure_html_response(
                create_page(
                    content='<div class="container"><h1>Authorization request expired</h1>'
                    "<p>Please reconnect from your MCP client.</p></div>",
                    title="Expired",
                ),
                status_code=400,
            )

        expected = settings.mcp_oauth_password.get_secret_value()
        if not expected or not hmac.compare_digest(password, expected):
            base = str(self.base_url).rstrip("/")
            return RedirectResponse(f"{base}/login?txn={txn}&error=Incorrect+password", status_code=303)

        del self._pending[txn]
        client, params = pending.client, pending.params
        if client.client_id is None:
            raise TokenError("invalid_client", "Client ID is required")

        code_value = secrets.token_hex(32)
        self.auth_codes[code_value] = AuthorizationCode(
            code=code_value,
            client_id=client.client_id,
            redirect_uri=params.redirect_uri,
            redirect_uri_provided_explicitly=params.redirect_uri_provided_explicitly,
            scopes=params.scopes or [],
            expires_at=time.time() + AUTH_CODE_EXPIRY_SECONDS,
            code_challenge=params.code_challenge,
            resource=params.resource,
        )
        redirect_uri = construct_redirect_uri(str(params.redirect_uri), code=code_value, state=params.state)
        return RedirectResponse(redirect_uri, status_code=303)

    def get_routes(self, mcp_path: str | None = None) -> list[Route]:
        routes = super().get_routes(mcp_path)
        routes.append(Route("/login", endpoint=self._handle_login_get, methods=["GET"]))
        routes.append(Route("/login", endpoint=self._handle_login_post, methods=["POST"]))
        return routes

    # --- Codes / tokens ---
    async def load_authorization_code(
        self,
        client: OAuthClientInformationFull,
        authorization_code: str,
    ) -> AuthorizationCode | None:
        code = self.auth_codes.get(authorization_code)
        if code is None:
            return None
        if code.client_id != client.client_id or code.expires_at < time.time():
            self.auth_codes.pop(authorization_code, None)
            return None
        return code

    async def exchange_authorization_code(
        self,
        client: OAuthClientInformationFull,
        authorization_code: AuthorizationCode,
    ) -> OAuthToken:
        if authorization_code.code not in self.auth_codes:
            raise TokenError("invalid_grant", "Authorization code not found or already used.")
        del self.auth_codes[authorization_code.code]
        if client.client_id is None:
            raise TokenError("invalid_client", "Client ID is required")
        return self._issue_tokens(client.client_id, authorization_code.scopes, authorization_code.resource)

    async def load_refresh_token(
        self,
        client: OAuthClientInformationFull,
        refresh_token: str,
    ) -> RefreshToken | None:
        token = self.refresh_tokens.get(refresh_token)
        if token is None or token.client_id != client.client_id:
            return None
        return token

    async def exchange_refresh_token(
        self,
        client: OAuthClientInformationFull,
        refresh_token: RefreshToken,
        scopes: list[str],
    ) -> OAuthToken:
        if not set(scopes).issubset(set(refresh_token.scopes)):
            raise TokenError("invalid_scope", "Requested scopes exceed those authorized by the refresh token.")
        if client.client_id is None:
            raise TokenError("invalid_client", "Client ID is required")
        self._revoke(access=self._refresh_to_access.get(refresh_token.token), refresh=refresh_token.token)
        return self._issue_tokens(client.client_id, scopes, refresh_token.resource)

    async def load_access_token(self, token: str) -> AccessToken | None:
        access = self.access_tokens.get(token)
        if access is None:
            return None
        if access.expires_at is not None and access.expires_at < time.time():
            self._revoke(access=token)
            return None
        return access

    async def verify_token(self, token: str) -> AccessToken | None:
        return await self.load_access_token(token)

    async def revoke_token(self, token: AccessToken | RefreshToken) -> None:
        if isinstance(token, AccessToken):
            self._revoke(access=token.token)
        else:
            self._revoke(refresh=token.token)

    def _issue_tokens(self, client_id: str, scopes: list[str], resource: str | None) -> OAuthToken:
        access_value = secrets.token_hex(32)
        refresh_value = secrets.token_hex(32)
        expires_at = int(time.time() + ACCESS_TOKEN_EXPIRY_SECONDS)
        self.access_tokens[access_value] = AccessToken(
            token=access_value,
            client_id=client_id,
            scopes=scopes,
            expires_at=expires_at,
            resource=resource,
        )
        self.refresh_tokens[refresh_value] = RefreshToken(
            token=refresh_value,
            client_id=client_id,
            scopes=scopes,
            expires_at=None,
            resource=resource,
        )
        self._access_to_refresh[access_value] = refresh_value
        self._refresh_to_access[refresh_value] = access_value
        return OAuthToken(
            access_token=access_value,
            token_type="Bearer",
            expires_in=ACCESS_TOKEN_EXPIRY_SECONDS,
            refresh_token=refresh_value,
            scope=" ".join(scopes),
        )

    def _revoke(self, access: str | None = None, refresh: str | None = None) -> None:
        if access and access in self.access_tokens:
            del self.access_tokens[access]
            linked_refresh = self._access_to_refresh.pop(access, None)
            if linked_refresh:
                self.refresh_tokens.pop(linked_refresh, None)
                self._refresh_to_access.pop(linked_refresh, None)
        if refresh and refresh in self.refresh_tokens:
            del self.refresh_tokens[refresh]
            linked_access = self._refresh_to_access.pop(refresh, None)
            if linked_access:
                self.access_tokens.pop(linked_access, None)
                self._access_to_refresh.pop(linked_access, None)
