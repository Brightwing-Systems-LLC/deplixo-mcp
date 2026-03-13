"""HTTP transport for the Brightwing MCP server."""
import uvicorn
from starlette.middleware.cors import CORSMiddleware
from mcp.server.transport_security import TransportSecuritySettings

from server import mcp

# Override settings directly before running
mcp.settings.host = "0.0.0.0"
mcp.settings.port = 8000
mcp.settings.streamable_http_path = "/"
mcp.settings.transport_security = TransportSecuritySettings(
    enable_dns_rebinding_protection=True,
    allowed_hosts=["mcp.brightwing.app"],
    allowed_origins=[
        "https://mcp.brightwing.app",
        "https://claude.ai",
        "https://*.claude.ai",
    ],
)


def create_app():
    """Create the Starlette app with CORS middleware."""
    app = mcp.streamable_http_app()
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "https://claude.ai",
            "https://*.claude.ai",
            "https://mcp.brightwing.app",
        ],
        allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
        allow_headers=["*"],
        allow_credentials=True,
    )
    return app


if __name__ == "__main__":
    app = create_app()
    config = uvicorn.Config(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info",
    )
    server = uvicorn.Server(config)
    server.run()
