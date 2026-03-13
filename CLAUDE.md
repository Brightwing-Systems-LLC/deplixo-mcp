# Brightwing MCP Server

## Overview
MCP server for deploying web apps to Brightwing Launch (brightwing.app). No API key required — zero friction.

## Tools
- `brightwing_deploy` - Deploy HTML/JS/CSS code and get a live URL instantly

## Configuration
Optional environment variable:
- `BRIGHTWING_API_URL` - API URL (default: https://brightwing.app)

## Development
```bash
uv sync
uv run python server.py  # stdio transport
uv run python http_server.py  # HTTP transport (for mcp.brightwing.app)
```

## Deployment
Uses docker-compose.bws.yml for shared infrastructure deployment.
Container connects to bws_network, served via Caddy at mcp.brightwing.app.
