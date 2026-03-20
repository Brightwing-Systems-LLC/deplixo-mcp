"""HTTP transport for the Deplixo MCP server."""
import logging
import time
from pathlib import Path

import uvicorn
from starlette.middleware.cors import CORSMiddleware
from starlette.requests import Request
from starlette.responses import FileResponse, JSONResponse, PlainTextResponse, Response
from starlette.routing import Route
from starlette.types import ASGIApp, Receive, Scope, Send
from mcp.server.transport_security import TransportSecuritySettings

from server import mcp

logger = logging.getLogger("deplixo-mcp")

MAX_REQUEST_BODY_BYTES = 10 * 1024 * 1024  # 10 MB


class RequestBodyLimitMiddleware:
    """Reject requests with bodies larger than MAX_REQUEST_BODY_BYTES."""

    def __init__(self, app: ASGIApp, max_bytes: int = MAX_REQUEST_BODY_BYTES):
        self.app = app
        self.max_bytes = max_bytes

    async def __call__(self, scope: Scope, receive: Receive, send: Send):
        if scope["type"] == "http":
            content_length = 0
            for header_name, header_value in scope.get("headers", []):
                if header_name == b"content-length":
                    content_length = int(header_value)
                    break
            if content_length > self.max_bytes:
                response = Response(
                    content=f"Request body too large (max {self.max_bytes // 1_000_000}MB)",
                    status_code=413,
                )
                await response(scope, receive, send)
                return
        await self.app(scope, receive, send)


class RequestLoggingMiddleware:
    """Log request method, path, and response status with timing."""

    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        start = time.monotonic()
        method = scope.get("method", "?")
        path = scope.get("path", "/")
        status_code = 0

        async def send_wrapper(message):
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message.get("status", 0)
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        except Exception:
            logger.exception("Unhandled exception on %s %s", method, path)
            raise
        finally:
            elapsed_ms = (time.monotonic() - start) * 1000
            level = logging.WARNING if status_code >= 400 else logging.INFO
            logger.log(level, "%s %s → %d (%.0fms)", method, path, status_code, elapsed_ms)


# Override settings directly before running
mcp.settings.host = "0.0.0.0"
mcp.settings.port = 8000
mcp.settings.streamable_http_path = "/"
mcp.settings.transport_security = TransportSecuritySettings(
    enable_dns_rebinding_protection=True,
    allowed_hosts=["mcp.deplixo.com"],
    allowed_origins=[
        "https://mcp.deplixo.com",
        "https://claude.ai",
        "https://*.claude.ai",
    ],
)


OPENAI_VERIFICATION_TOKEN = "d83b7MzyCoqobditKIKjryE5TYCv-fXc3C6Lj5a9wmA"
FAVICON_PATH = Path(__file__).parent / "favicon.ico"
_START_TIME = time.time()


async def favicon(request: Request) -> FileResponse:
    """Serve favicon for domain verification."""
    return FileResponse(FAVICON_PATH, media_type="image/x-icon")


async def openai_apps_challenge(request: Request) -> PlainTextResponse:
    """OpenAI domain verification for ChatGPT App Directory."""
    return PlainTextResponse(OPENAI_VERIFICATION_TOKEN)


async def health(request: Request) -> JSONResponse:
    """Health check endpoint for Docker and monitoring."""
    return JSONResponse({
        "status": "ok",
        "uptime_seconds": int(time.time() - _START_TIME),
    })


def create_app():
    """Create the Starlette app with CORS and request body limit middleware."""
    app = mcp.streamable_http_app()
    app.routes.append(Route("/favicon.ico", favicon))
    app.routes.append(Route("/health", health))
    app.routes.append(
        Route("/.well-known/openai-apps-challenge", openai_apps_challenge)
    )
    app.add_middleware(RequestBodyLimitMiddleware, max_bytes=MAX_REQUEST_BODY_BYTES)
    app.add_middleware(RequestLoggingMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "https://claude.ai",
            "https://*.claude.ai",
            "https://mcp.deplixo.com",
        ],
        allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
        allow_headers=["*"],
        allow_credentials=True,
    )
    return app


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    app = create_app()
    config = uvicorn.Config(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info",
        timeout_keep_alive=75,  # Keep connections alive longer (Caddy default is 60s)
        limit_concurrency=50,   # Prevent overload
    )
    server = uvicorn.Server(config)
    server.run()
