"""Mount MCP Streamable HTTP under FastAPI with API-key gate."""

from __future__ import annotations

from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Receive, Scope, Send

from app.core.config import settings
from app.mcp.server import mcp
from mcp.server.transport_security import TransportSecuritySettings

# Built once; session_manager starts in FastAPI lifespan.
mcp_http_app = mcp.streamable_http_app(
    streamable_http_path="/",
    json_response=True,
    stateless_http=True,
    transport_security=TransportSecuritySettings(
        enable_dns_rebinding_protection=False,
    ),
    host="0.0.0.0",
)


class McpApiKeyMiddleware:
    """Require Authorization: Bearer <MCP_API_KEY> or X-API-Key on /mcp*."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        path = scope.get("path") or ""
        if not path.startswith("/mcp"):
            await self.app(scope, receive, send)
            return

        if scope.get("method") == "OPTIONS":
            await self.app(scope, receive, send)
            return

        headers = {k.decode().lower(): v.decode() for k, v in scope.get("headers") or []}
        provided = headers.get("x-api-key")
        auth = headers.get("authorization") or ""
        if auth.lower().startswith("bearer "):
            provided = auth[7:].strip()

        expected = settings.MCP_API_KEY
        if not expected or provided != expected:
            response = JSONResponse(
                {"detail": "Invalid or missing MCP API key", "code": "mcp_unauthorized"},
                status_code=401,
            )
            await response(scope, receive, send)
            return

        await self.app(scope, receive, send)


def extract_mcp_api_key(request: Request) -> str | None:
    key = request.headers.get("x-api-key")
    if key:
        return key
    auth = request.headers.get("authorization") or ""
    if auth.lower().startswith("bearer "):
        return auth[7:].strip()
    return None
