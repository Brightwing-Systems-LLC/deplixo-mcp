"""HTTP transport for the Brightwing MCP server."""
from mcp.server.transport_security import TransportSecuritySettings

from server import mcp

# Override settings directly before running
mcp.settings.host = "0.0.0.0"
mcp.settings.port = 8000
mcp.settings.transport_security = TransportSecuritySettings(
    enable_dns_rebinding_protection=True,
    allowed_hosts=["mcp.brightwing.app"],
    allowed_origins=["https://mcp.brightwing.app"],
)

if __name__ == "__main__":
    mcp.run(transport="streamable-http")
