"""Tests for the HTTP server wrapper."""
from http_server import create_app, mcp


def test_create_app_returns_starlette_app():
    app = create_app()
    assert hasattr(app, "router")


def test_create_app_callable():
    """The app returned by create_app is a valid ASGI/Starlette app."""
    app = create_app()
    assert callable(app)


def test_mcp_settings_configured():
    assert mcp.settings.host == "0.0.0.0"
    assert mcp.settings.port == 8000
    assert mcp.settings.streamable_http_path == "/"


def test_transport_security_settings():
    security = mcp.settings.transport_security
    assert security.enable_dns_rebinding_protection is True
    assert "mcp.deplixo.com" in security.allowed_hosts
    assert "https://claude.ai" in security.allowed_origins
    assert "https://mcp.deplixo.com" in security.allowed_origins


class TestRateLimitMiddleware:
    def test_rate_limiter_allows_normal_traffic(self):
        from http_server import RateLimitMiddleware
        rl = RateLimitMiddleware(app=None, max_requests=10, window_seconds=60)
        # Simulate IP extraction
        scope = {"type": "http", "path": "/", "headers": [], "client": ("1.2.3.4", 1234)}
        ip = rl._get_client_ip(scope)
        assert ip == "1.2.3.4"

    def test_rate_limiter_extracts_xff_rightmost(self):
        from http_server import RateLimitMiddleware
        rl = RateLimitMiddleware(app=None)
        scope = {
            "type": "http", "path": "/",
            "headers": [(b"x-forwarded-for", b"spoofed, real_client")],
            "client": ("127.0.0.1", 1234),
        }
        assert rl._get_client_ip(scope) == "real_client"

    def test_rate_limiter_exempts_health(self):
        from http_server import RateLimitMiddleware
        assert "/health" in RateLimitMiddleware.EXEMPT_PATHS
        assert "/favicon.ico" in RateLimitMiddleware.EXEMPT_PATHS
