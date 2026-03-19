# Deplixo MCP — Marketplace Submission Plan

Comprehensive task list for submitting to both the **Claude Connector Marketplace** and the **ChatGPT App Store (OpenAI Apps SDK)**.

---

## 1. Safety / Tool Annotations (BLOCKING — both platforms) ✅

Both platforms list missing annotations as the #1 rejection reason.

- [x] **Add `readOnlyHint: false`** to `deplixo_deploy` — the tool creates resources
- [x] **Add `destructiveHint: false`** — deployments create, they don't delete/overwrite
- [x] **Add `openWorldHint: true`** (OpenAI-specific) — the tool publishes content to a public URL
- [x] **Add `idempotentHint: false`** — each call creates a new deployment (unless same slug)

Done: Added `ToolAnnotations` to `@mcp.tool()` decorator in `server.py`. Verified by `test_tool_annotations` test.

---

## 2. CORS Configuration (Claude marketplace requirement) ✅

Claude docs: "CORS properly configured for browser clients." Claude.ai calls the MCP server from the browser.

- [x] **Verify FastMCP's streamable-http transport handles CORS** — it does not; no built-in CORS middleware
- [x] **Add CORS middleware** — added Starlette `CORSMiddleware` to `http_server.py` allowing `https://claude.ai` and `https://*.claude.ai`
- [x] **Update `allowed_origins` in `TransportSecuritySettings`** — added Claude's origins (was only `mcp.deplixo.com`, which would reject Claude.ai requests)
- [x] **Test CORS preflight** — verified OPTIONS request from `Origin: https://claude.ai` returns `access-control-allow-origin: https://claude.ai`, `access-control-allow-methods: GET, POST, DELETE, OPTIONS`, `access-control-allow-headers: content-type`, `access-control-allow-credentials: true`
- [x] **Caddy not duplicating headers** — Caddy proxies through cleanly; CORS headers come from the app layer only

---

## 3. OAuth 2.0 / Authentication (Claude marketplace) ✅

Claude requires OAuth 2.0 if auth is needed. Deplixo Deploy has **no auth**.

- [x] **Confirm no-auth is acceptable** for the Claude directory — the submission guide says "if required" so this is fine
- [ ] **Document clearly in submission** that no authentication is required (zero-friction design)

For OpenAI: no-auth apps are supported. No action needed.

---

## 4. HTTPS / TLS (both platforms) ✅

- [x] **Verify `mcp.deplixo.com` has valid TLS cert** — TLSv1.3, issued by Let's Encrypt (E8), CN=mcp.deplixo.com, valid 2026-03-13 to 2026-06-11
- [x] **Test certificate chain** — `SSL certificate verify ok`, ALPN h2 accepted
- [x] **Auto-renewal** — Caddy handles Let's Encrypt renewal automatically

---

## 5. Privacy Policy (BLOCKING — both platforms) ✅

- [x] **Write privacy policy** covering: data collection, usage, retention, sharing, user controls, contact info
- [x] **Publish at `deplixo.com/privacy`** — live and accessible
- [ ] **Link in submission forms** for both platforms

Sections present: Information We Collect, How We Use Your Information, Data Sharing, Data Retention, Data Security, Your Rights, Changes to This Policy, Contact Us.

---

## 6. Support Channels (BLOCKING — both platforms) ✅

- [x] **Set up support email** — `support@deplixo.com` (visible in footer at deplixo.com)
- [ ] **Consider a public issue tracker** (GitHub Issues on the repo, or a support page)
- [ ] **Document support contact** in submission forms and privacy policy

---

## 7. Documentation & Usage Examples (Claude — minimum 3 examples) ✅

Claude requires "minimum 3 working examples with user prompts." This content goes directly into the **Claude marketplace submission form** and **OpenAI Apps dashboard** — not a file in the repo.

Usage examples drafted in `plans/usage-examples.md` — 4 examples covering single-file, multi-file React, persistent storage, and remix workflows.

- [ ] **Draft submission documentation** with these sections:
  - Server Description
  - Features / Key Capabilities
  - Setup Instructions (how to connect — just add the URL, no config needed)
  - Authentication Details (none required)
  - Usage Examples (minimum 3)
  - Privacy Policy link
  - Support contact

- [ ] **Prepare 3+ usage examples** in the format Claude wants:

  **Example 1 — Simple HTML app:**
  > User prompt: "Deploy a landing page with a gradient background and centered headline"
  > → Tool deploys single-file HTML → Returns claim link (1-hour expiry, free to claim)

  **Example 2 — Multi-file React app:**
  > User prompt: "Build me a todo app with React and deploy it"
  > → Tool deploys multi-file app with index.html + app.js + style.css → Returns claim link

  **Example 3 — App with persistent storage:**
  > User prompt: "Create a notes app that saves data between sessions"
  > → Tool deploys app using window.deplixo.db for persistence → Returns claim link

  **Example 4 (bonus) — Remix an existing app:**
  > User prompt: "Take app abc123 and add dark mode"
  > → Tool deploys remix with remixed_from parameter → Returns claim link for new app

---

## 8. Token Limit Compliance (Claude) ✅

Claude: "Maximum 25,000 tokens per tool result."

- [x] **Verify tool responses stay under 25,000 tokens** — current responses are short text strings (~200 chars)
- [x] **Error response truncation** — error messages from the API are now truncated to 5,000 chars in `server.py`. Verified by `test_deploy_error_response_truncated` test.

---

## 9. Response Data Minimization (OpenAI) ✅

OpenAI: "return only data directly relevant to the user's request. Exclude diagnostic metadata, session IDs, timestamps."

- [x] **Review tool response format** — all fields are user-actionable (url, hash_id, source URL, claim_url), not diagnostic
- [x] **No extra fields leak** — response is constructed from specific `data.get()` calls, not passed through wholesale

---

## 10. Input Schema Minimization (OpenAI) ✅

OpenAI: "request the minimum information necessary."

- [x] **Review parameters** — all current params are justified:
  - `code` / `files` — the content to deploy (required)
  - `title` — user-facing metadata
  - `slug` — optional, power user feature
  - `remixed_from` — optional, attribution
- [x] Current design looks good. No changes needed.

---

## 11. Testing (BLOCKING — both platforms)

Claude: "Verify functionality on Claude.ai, Claude Desktop, and Claude Code."
OpenAI: "thorough testing... stability, responsiveness, and low latency."

### 11a. Write automated tests ✅
- [x] **Create `test_server.py`** with 8 unit tests:
  - Validation: no code or files → error
  - Validation: files without index.html → error
  - Successful single-file deployment (mock httpx)
  - Successful multi-file deployment (mock httpx)
  - API error handling (mock 500 response)
  - Error response truncation
  - Timeout handling
  - Tool annotations verification
- [ ] **Run tests in CI** — add pytest step to deploy.yml (or a separate test workflow)

### 11b. Manual platform testing
- [ ] **Test on Claude.ai** — add as remote MCP server, deploy an app
- [ ] **Test on Claude Desktop** — add server config, deploy an app
- [ ] **Test on Claude Code** — add via `claude mcp add`, deploy an app
- [ ] **Test on ChatGPT** — submit as MCP app, test deployment flow
- [ ] **Document test results** for submission

### 11c. Load / reliability testing
- [ ] **Verify server stays up under moderate load** — multiple concurrent deployments
- [ ] **Verify 30s timeout is adequate** for large multi-file deployments
- [ ] **Test error recovery** — what happens when deplixo.com API is down

---

## 12. Production Readiness (Claude) ✅

Claude: "General Availability (GA) status. Not marked beta/alpha/development."

- [x] **Audit all user-facing text** for beta/alpha/dev labels:
  - Server name: "Deplixo" — clean
  - Instructions text — clean
  - CLAUDE.md — clean
  - deplixo.com landing page — no beta/alpha/experimental labels found
- [ ] **Ensure monitoring is in place** — server health checks, uptime monitoring
- [ ] **Set up alerting** for downtime (e.g. UptimeRobot, Healthchecks.io)

---

## 13. Claude-Specific: IP Allowlisting

Claude docs mention allowlisting Claude IP addresses for firewall-protected servers.

- [ ] **Check if Caddy/server has IP restrictions** — if not (likely), no action needed
- [ ] If firewall exists, **allowlist Claude IPs** from docs.claude.com/en/api/ip-addresses

---

## 14. OpenAI-Specific: Developer Verification

OpenAI: "All submissions must come from verified individuals or organizations."
Misrepresentation or gaming the system may result in removal from the program.

### Steps:
- [ ] **Log in to the OpenAI Platform Dashboard** at [platform.openai.com](https://platform.openai.com)
- [ ] **Ensure you have the Owner role** on the Brightwing Systems LLC organization — only Owners can submit apps for review
- [ ] **Go to Settings → General** and complete identity verification — confirm your personal identity and affiliation with Brightwing Systems LLC
- [ ] **Ensure org details are accurate** — name, contact info, etc. match the real business entity
- [ ] **Add customer support contact details** — OpenAI requires "accurate, current" support info where end users can reach you (this ties into §6)
- [ ] **Submit apps via the Apps dashboard** at [platform.openai.com/apps-manage](https://platform.openai.com/apps-manage)

---

## 15. OpenAI-Specific: App Metadata

OpenAI requires polished metadata for marketplace listing.

- [ ] **App name**: "Deplixo" (clear, not generic)
- [ ] **App description**: concise explanation of instant web app deployment
- [ ] **Screenshots**: Create screenshots showing deployment flow and resulting live app
  - Must meet OpenAI's required dimensions
  - Must accurately represent functionality
- [ ] **Category selection**: Developer Tools / Deployment

---

## 16. OpenAI-Specific: Tool Invocation Status Text

OpenAI supports `_meta` fields for status text during tool execution.

- [ ] **Add invocation status text** (optional but polished):
  - `openai/toolInvocation/invoking`: "Deploying app..." (≤64 chars)
  - `openai/toolInvocation/invoked`: "App deployed" (≤64 chars)

---

## 17. OpenAI-Specific: Content Safety

OpenAI: "suitable for general audiences, including users aged 13-17."

- [ ] **Confirm deployed content filtering** — does the Deplixo API reject inappropriate content? If not, document that the tool is a deployment platform and content moderation is at the platform level
- [ ] **Ensure tool description doesn't encourage harmful use**

---

## 18. README / Public Documentation

Both platforms benefit from a polished public presence.

- [ ] **Write a proper README.md** for the repo with:
  - What it does (1-2 sentences)
  - Quick start (how to connect)
  - Tool reference
  - Examples
  - Links to deplixo.com, privacy policy, support
- [ ] **Ensure GitHub repo is public** (or has a public-facing docs page)

---

## Priority Order

### Must-do before submission (blockers):
1. ~~Safety annotations (§1)~~ ✅
2. ~~Privacy policy (§5)~~ ✅
3. ~~Support channels (§6)~~ ✅
4. ~~Documentation with 3+ examples (§7)~~ ✅ — see `plans/usage-examples.md`
5. ~~CORS verification/fix (§2)~~ ✅
6. ~~TLS verification (§4)~~ ✅
7. Platform testing — Claude.ai, Desktop, Code (§11b)
8. ~~GA status audit (§12)~~ ✅

### Should-do (strong improvement):
9. ~~Automated tests (§11a)~~ ✅
10. ~~Error response truncation (§8)~~ ✅
11. README (§18)
12. OpenAI developer verification (§14)
13. OpenAI app metadata & screenshots (§15)
14. Uptime monitoring (§12)

### Nice-to-have (polish):
15. OpenAI invocation status text (§16)
16. Load testing (§11c)
17. Content safety documentation (§17)
18. IP allowlisting check (§13)
