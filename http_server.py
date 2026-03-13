"""HTTP transport for the Brightwing MCP server."""
from server import mcp

# Override settings directly before running
mcp.settings.host = "0.0.0.0"
mcp.settings.port = 8000

if __name__ == "__main__":
    mcp.run(transport="streamable-http")
