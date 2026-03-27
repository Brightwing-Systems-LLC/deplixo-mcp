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

**CRITICAL: Do NOT SSH into the prod server to deploy.** Always commit and push to `main` — GitHub Actions handles deployment automatically. Do not run `git pull`, `docker compose`, or any other commands on the production server.

## MCP Instructions — Architecture

The `instructions=` block in `server.py` is intentionally **lean**. It does NOT
contain the full SDK reference. Instead, it tells AIs:

1. Call `deplixo_enhance` first to identify capabilities
2. **Fetch `https://deplixo.com/sdk?format=text`** before writing any code
3. Follow the Critical Quick Reference (top 5 bugs)
4. Follow the IMPORTANT RULES and "How to replace common stubs" lists

The full SDK reference lives in `deplixo/templates/pages/sdk.txt` — that is the
**single source of truth**. The MCP instructions point to it rather than
duplicating it.

**The five locations that must stay in sync:**

1. `deplixo/js/sdk/core.js` + `js/sdk/legos/` — The actual SDK code
2. `deplixo/templates/pages/sdk.txt` — Authoritative SDK reference (fetched by AIs)
3. `deplixo/primitives/<name>/` — **Registry files (snippets, anti-patterns,
   manifests). These take PRIORITY over `_SDK_SNIPPETS` in server.py.** The
   enhance tool returns these directly to AI clients. If you update server.py
   but not the primitive files, AIs see the OLD snippet.
   - `snippet.js` — Code pattern AIs copy-paste (HIGHEST priority)
   - `anti_patterns.md` — Mistakes shown as "CRITICAL mistakes to avoid"
   - `manifest.yaml` — Method descriptions, deploy flags
   - `reference.md` — Extended reference docs
4. **This repo: `server.py`** — `_SDK_SNIPPETS` (fallback), IMPORTANT RULES,
   "How to replace common stubs", Critical Quick Reference
5. `deplixo/api/v1/enhance.py` — Enhance LLM prompt and exclusion rules

**When to update what:**
- New/changed SDK feature → update ALL FIVE
- New anti-pattern → `primitives/<name>/anti_patterns.md` + server.py NEVER rule
- New "use X instead of Y" rule → server.py "How to replace common stubs"
- Changed enhance behavior (which primitives are recommended) → `enhance.py`

See `deplixo/CLAUDE.md` "SDK Documentation — KEEP ALL FIVE IN SYNC" for the
full checklist.
