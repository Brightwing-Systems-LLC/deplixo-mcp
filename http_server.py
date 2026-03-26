"""HTTP transport for the Deplixo MCP server."""
import logging
import os
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


class RateLimitMiddleware:
    """In-memory per-IP rate limiter.

    Limits each IP to max_requests within window_seconds.
    Uses a simple sliding-window counter per IP.
    Exempt paths (health, favicon) are not rate limited.
    """

    EXEMPT_PATHS = {"/health", "/favicon.ico", "/.well-known/openai-apps-challenge"}

    def __init__(self, app: ASGIApp, max_requests: int = 30, window_seconds: int = 60):
        self.app = app
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._requests: dict[str, list[float]] = {}

    def _get_client_ip(self, scope: "Scope") -> str:
        """Extract client IP, preferring X-Forwarded-For (rightmost entry)."""
        for name, value in scope.get("headers", []):
            if name == b"x-forwarded-for":
                parts = value.decode().split(",")
                return parts[-1].strip()  # rightmost = added by trusted proxy
        client = scope.get("client")
        return client[0] if client else "unknown"

    async def __call__(self, scope: Scope, receive: Receive, send: Send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        path = scope.get("path", "/")
        if path in self.EXEMPT_PATHS:
            await self.app(scope, receive, send)
            return

        ip = self._get_client_ip(scope)
        now = time.time()
        cutoff = now - self.window_seconds

        # Clean old entries and count recent
        entries = self._requests.get(ip, [])
        entries = [t for t in entries if t > cutoff]
        entries.append(now)
        self._requests[ip] = entries

        # Periodic cleanup of stale IPs (every ~100 requests)
        if len(self._requests) > 1000:
            stale = [k for k, v in self._requests.items() if not v or v[-1] < cutoff]
            for k in stale:
                del self._requests[k]

        if len(entries) > self.max_requests:
            response = Response(
                content='{"error": "rate_limited", "message": "Too many requests. Please slow down.", "retryAfter": 60}',
                status_code=429,
                media_type="application/json",
            )
            await response(scope, receive, send)
            return

        await self.app(scope, receive, send)


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
    """Log request method, path, and response status with timing.

    In dev mode (DEPLIXO_API_URL=http://localhost:*), logs full request
    and response bodies for debugging MCP protocol issues.
    """

    def __init__(self, app: ASGIApp):
        self.app = app
        self._verbose = os.environ.get("DEPLIXO_API_URL", "").startswith("http://localhost")

    async def __call__(self, scope: Scope, receive: Receive, send: Send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        start = time.monotonic()
        method = scope.get("method", "?")
        path = scope.get("path", "/")

        # Skip noisy reload polling
        if path == "/__reload__/events/":
            await self.app(scope, receive, send)
            return

        if not self._verbose:
            # Production: simple one-line log
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
            return

        # === Dev mode: verbose logging ===
        import json as _json

        headers = {k.decode(): v.decode() for k, v in scope.get("headers", [])}
        host = headers.get("host", "?")
        origin = headers.get("origin", "-")
        session_id = headers.get("mcp-session-id", "-")
        logger.info(
            "\n━━━ INCOMING %s %s (host=%s, origin=%s, session=%s)",
            method, path, host, origin,
            session_id[:16] + "…" if len(session_id) > 16 else session_id,
        )

        # Capture request body
        body_chunks: list[bytes] = []

        async def receive_wrapper():
            msg = await receive()
            if msg.get("type") == "http.request":
                chunk = msg.get("body", b"")
                if chunk:
                    body_chunks.append(chunk)
            return msg

        # Capture response
        status_code = 0
        response_content_type = ""
        response_body_chunks: list[bytes] = []

        async def send_wrapper(message):
            nonlocal status_code, response_content_type
            if message["type"] == "http.response.start":
                status_code = message.get("status", 0)
                resp_headers = {k.decode(): v.decode() for k, v in message.get("headers", [])}
                response_content_type = resp_headers.get("content-type", "?")
            if message["type"] == "http.response.body":
                chunk = message.get("body", b"")
                if chunk:
                    response_body_chunks.append(chunk)
            await send(message)

        try:
            await self.app(scope, receive_wrapper, send_wrapper)
        except Exception:
            logger.exception("Unhandled exception on %s %s", method, path)
            raise
        finally:
            elapsed_ms = (time.monotonic() - start) * 1000

            # Log complete request body
            raw_body = b"".join(body_chunks)
            if raw_body:
                try:
                    parsed = _json.loads(raw_body)
                    logger.info("  REQUEST:\n%s", _json.dumps(parsed, indent=2))
                except (_json.JSONDecodeError, UnicodeDecodeError):
                    logger.info("  REQUEST (raw):\n%s", raw_body.decode(errors="replace"))

            # Log complete response
            resp_raw = b"".join(response_body_chunks)
            logger.info("  RESPONSE: %d %s (%d bytes, %.0fms)", status_code, response_content_type, len(resp_raw), elapsed_ms)
            if resp_raw:
                try:
                    resp_text = resp_raw.decode()
                    if "text/event-stream" in response_content_type:
                        # Parse SSE and pretty-print the JSON-RPC data
                        for line in resp_text.split("\n"):
                            if line.startswith("data: "):
                                try:
                                    data = _json.loads(line[6:])
                                    # Extract text content for readability
                                    result = data.get("result", {})
                                    content = result.get("content", [])
                                    if content:
                                        text = "\n".join(c.get("text", "") for c in content if c.get("type") == "text")
                                        logger.info("  RESPONSE content:\n%s", text)
                                    else:
                                        logger.info("  RESPONSE data:\n%s", _json.dumps(data, indent=2))
                                except _json.JSONDecodeError:
                                    logger.info("  RESPONSE SSE line: %s", line)
                            elif line.strip() and not line.startswith("event:"):
                                logger.info("  RESPONSE SSE: %s", line)
                    else:
                        logger.info("  RESPONSE body:\n%s", resp_text)
                except UnicodeDecodeError:
                    logger.info("  RESPONSE body: (binary, %d bytes)", len(resp_raw))

            logger.info("━━━ DONE %s %s → %d (%.0fms)\n", method, path, status_code, elapsed_ms)


# Override settings directly before running
mcp.settings.host = "0.0.0.0"
mcp.settings.port = 8000
mcp.settings.streamable_http_path = "/"

_is_dev = os.environ.get("DEPLIXO_API_URL", "").startswith("http://localhost")
_ngrok_host = os.environ.get("NGROK_HOST", "")  # e.g. "abc123.ngrok-free.app"

mcp.settings.transport_security = TransportSecuritySettings(
    enable_dns_rebinding_protection=not _is_dev,  # disable in dev for ngrok compatibility
    allowed_hosts=[
        "mcp.deplixo.com",
        *(["localhost", "127.0.0.1", "localhost:8000", "127.0.0.1:8000"] if _is_dev else []),
        *([_ngrok_host] if _ngrok_host else []),
        *(["keyton.ngrok.dev"] if _is_dev else []),
    ],
    allowed_origins=[
        "https://mcp.deplixo.com",
        # Claude
        "https://claude.ai",
        "https://*.claude.ai",
        # ChatGPT
        "https://chatgpt.com",
        "https://*.chatgpt.com",
        "https://chat.openai.com",
        "https://*.openai.com",
        # Dev
        *(["http://localhost:8000", "http://127.0.0.1:8000", "http://localhost:8895", "http://127.0.0.1:8895"] if _is_dev else []),
        *([f"https://{_ngrok_host}"] if _ngrok_host else []),
        *(["https://keyton.ngrok.dev"] if _is_dev else []),
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
    app.add_middleware(RateLimitMiddleware, max_requests=30, window_seconds=60)
    app.add_middleware(RequestLoggingMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "https://mcp.deplixo.com",
            # Claude
            "https://claude.ai",
            "https://*.claude.ai",
            # ChatGPT
            "https://chatgpt.com",
            "https://*.chatgpt.com",
            "https://chat.openai.com",
            "https://*.openai.com",
        ],
        allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
        allow_headers=["*"],
        allow_credentials=True,
    )
    return app


if __name__ == "__main__":
    _log_level = logging.DEBUG if _is_dev else logging.WARNING
    logging.basicConfig(
        level=_log_level,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    if _is_dev:
        # In dev: silence noisy libraries, keep our logs verbose
        logging.getLogger("mcp").setLevel(logging.WARNING)
        logging.getLogger("httpx").setLevel(logging.WARNING)
        logging.getLogger("httpcore").setLevel(logging.WARNING)
    app = create_app()
    config = uvicorn.Config(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="debug" if _is_dev else "warning",
        timeout_keep_alive=75,  # Keep connections alive longer (Caddy default is 60s)
        limit_concurrency=50,   # Prevent overload
    )
    server = uvicorn.Server(config)
    server.run()
