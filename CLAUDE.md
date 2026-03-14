# Deplixo MCP Server

## Overview
MCP server for deploying web apps to Deplixo (deplixo.com). No API key required — zero friction.

## Tools
- `deplixo_deploy` - Deploy HTML/JS/CSS code and get a live URL instantly

## Configuration
Optional environment variable:
- `DEPLIXO_API_URL` - API URL (default: https://deplixo.com)

## Development
```bash
uv sync
uv run python server.py  # stdio transport
uv run python http_server.py  # HTTP transport (for mcp.deplixo.com)
```

## Deployment
Uses docker-compose.bws.yml for shared infrastructure deployment.
Container connects to bws_network, served via Caddy at mcp.deplixo.com.
