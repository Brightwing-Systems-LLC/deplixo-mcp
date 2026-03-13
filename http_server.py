"""HTTP transport for the Brightwing MCP server.

The MCP library reads host/port from MCP_HTTP_HOST and MCP_HTTP_PORT env vars.
"""
import os

# Set host/port via env vars that the MCP library reads
os.environ.setdefault("MCP_HTTP_HOST", "0.0.0.0")
os.environ.setdefault("MCP_HTTP_PORT", os.environ.get("PORT", "8000"))

from server import mcp

if __name__ == "__main__":
    mcp.run(transport="streamable-http")
