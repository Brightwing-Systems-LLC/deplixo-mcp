# Deplixo MCP Server recipes

# Development
dev:
    uv run python server.py

dev-http:
    uv run python http_server.py

# Local dev: HTTP server pointing to local Django (verbose logging, ngrok-compatible)
dev-local:
    DEPLIXO_API_URL=http://localhost:8895 uv run python http_server.py

# =============================================================================
# Production Commands
# =============================================================================

PROD_COMPOSE := "-f docker-compose.bws.yml"

# Pull latest code (reset to match remote — prod should never have local changes)
prod-pull:
    git remote prune origin
    git fetch origin main
    git reset --hard origin/main

# Build prod image
prod-build:
    docker compose {{PROD_COMPOSE}} build web

# Bring up prod services
prod-up:
    docker compose {{PROD_COMPOSE}} down --remove-orphans
    docker compose {{PROD_COMPOSE}} up -d web

# Deploy updates (pull + build + restart)
prod-deploy: prod-pull prod-build prod-up prod-cleanup

# View production logs
prod-logs:
    docker compose {{PROD_COMPOSE}} logs -f

# Restart production services
prod-restart:
    docker compose {{PROD_COMPOSE}} restart

# Stop production services
prod-down:
    docker compose {{PROD_COMPOSE}} down

# Clean up unused Docker resources
prod-cleanup:
    docker image prune -af
    docker builder prune -af
