"""HTTP transport for the Brightwing MCP server."""
import os
from server import mcp

if __name__ == "__main__":
    mcp.run(transport="streamable-http", host="0.0.0.0", port=int(os.environ.get("PORT", "8000")))
