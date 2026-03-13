# Brightwing MCP Server recipes

# Development
dev:
    uv run python server.py

dev-http:
    uv run python http_server.py

# =============================================================================
# Production Commands
# =============================================================================

# Deploy updates
prod-deploy:
    git pull origin main
    docker compose up -d --build

# View production logs
prod-logs:
    docker compose logs -f

# Restart production services
prod-restart:
    docker compose restart

# Stop production services
prod-down:
    docker compose down
