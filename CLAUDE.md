# Brightwing MCP Server

## Overview
MCP server for deploying web apps and publishing blog posts to Brightwing Launch (brightwing.app).

## Tools
- `brightwing_deploy` - Deploy HTML/JS/CSS code and get a live URL
- `brightwing_blog_publish` - Publish markdown blog posts

## Configuration
Requires two environment variables:
- `BRIGHTWING_API_KEY` - Your API key from https://brightwing.app/dashboard/api-key/
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
