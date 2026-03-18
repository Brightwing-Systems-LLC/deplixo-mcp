"""Deplixo MCP Server - Deploy AI apps instantly."""
import os
import httpx
from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations

DEPLIXO_API_URL = os.environ.get("DEPLIXO_API_URL", "https://deplixo.com")


def _format_suggestions(suggestions: dict) -> list[str]:
    """Format code analysis suggestions into human-readable text lines."""
    lines = ["", "⚠ This app has issues that need fixing:"]

    if suggestions.get("intent"):
        lines.extend(["", f'Intent: "{suggestions["intent"]}"'])

    # Regex-detected stubs
    if suggestions.get("stubs"):
        lines.append("")
        lines.append("Stub patterns detected:")
        for stub in suggestions["stubs"]:
            lines.append(f"  - {stub['message']}")

    # Missing primitives (regex)
    if suggestions.get("missing_primitives"):
        lines.append("")
        lines.append("Missing Deplixo primitives:")
        for mp in suggestions["missing_primitives"]:
            lines.append(f"  - {mp['message']}")
            if mp.get("fix"):
                lines.append(f"    Fix: {mp['fix']}")

    # LLM-detected functional gaps
    if suggestions.get("functional_gaps"):
        lines.append("")
        lines.append("Functional gaps:")
        for gap in suggestions["functional_gaps"]:
            lines.append(f"  - {gap.get('feature', 'Unknown feature')}: "
                         f"{gap.get('current_state', '')}")
            if gap.get("fix_code"):
                lines.append(f"    Fix with {gap.get('primitive', 'Deplixo SDK')}:")
                for code_line in gap["fix_code"].strip().split("\n"):
                    lines.append(f"      {code_line}")

    # Missed opportunities (informational, non-blocking)
    if suggestions.get("missed_opportunities"):
        lines.append("")
        lines.append("Suggestions (not blocking, but would improve the app):")
        for opp in suggestions["missed_opportunities"]:
            lines.append(f"  - {opp}")

    lines.extend([
        "",
        "Please fix these issues and redeploy. The user expects a working app.",
    ])
    return lines

mcp = FastMCP(
    "Deplixo",
    instructions=(
        "Use the deplixo_deploy tool to deploy web apps to Deplixo. "
        "When the user asks you to deploy, share, host, or publish their app, "
        "use this tool. It returns a live URL instantly — no account required.\n\n"
        "IMPORTANT: Apps can be single-file (pass `code`) or multi-file (pass "
        "`files` dict with paths like index.html, style.css, app.js). "
        "Multi-file apps have each file served at its path under the app URL. "
        "For React apps, use CDN imports (unpkg.com/react, unpkg.com/react-dom, "
        "unpkg.com/@babel/standalone) with <script type=\"text/babel\"> — do NOT "
        "use npm, create-react-app, Vite, or any build tools. "
        "For Vue, Svelte, Three.js, etc., use their CDN builds the same way.\n\n"
        "CRITICAL: After deploying, you MUST show the user BOTH the live app URL "
        "AND the claim URL as clickable links in your response. Do NOT omit, "
        "summarize, or paraphrase the claim URL — the user needs the exact link "
        "to manage their app. Without it, they lose access permanently. "
        "Unclaimed apps expire after 24 hours. Claiming is free and extends the app to 7 days. Paid plans (Personal/Pro) keep apps permanently.\n\n"
        "Updating apps: When the deploy response includes app_id and claim_token, "
        "keep them in context. If the user asks to update the app, pass app_id "
        "and claim_token in the next deploy call to update in-place at the same URL."
    ),
)


@mcp.tool(
    annotations=ToolAnnotations(
        readOnlyHint=False,
        destructiveHint=False,
        openWorldHint=True,
        idempotentHint=False,
    )
)
async def deplixo_deploy(
    code: str = "",
    files: dict[str, str] | None = None,
    title: str = "",
    slug: str = "",
    remixed_from: str = "",
    app_id: str = "",
    claim_token: str = "",
) -> str:
    """Deploy a web app to Deplixo and get a live URL.

    Apps can be single-file or multi-file. For single-file apps, pass the HTML
    as `code`. For multi-file apps (separate CSS, JS, assets), pass a `files`
    dict mapping file paths to content — must include "index.html".

    For React, Vue, or other frameworks: use CDN imports (e.g. unpkg.com/react@18,
    unpkg.com/react-dom@18, unpkg.com/@babel/standalone) — do NOT use npm or
    build tools.

    To update an existing app, pass the app_id and claim_token from a previous
    deploy response. This updates the app in-place at the same URL.

    ## Deplixo SDK (automatically injected into every deployed app)

    Every deployed app gets `window.deplixo` with these APIs:

    ### Collections (shared data — use this for any list of items)
    All data is shared across ALL visitors in real-time.
    ALWAYS pass { personal: true } or { personal: false } (see patterns below).
      const recipes = deplixo.db.collection("recipes", { personal: false });
      await recipes.add({ title: "Pasta", photo: url })  → { id, value }
      await recipes.list()                                → [{ id, value, author }]
      await recipes.get(id)                               → { id, value, author }
      await recipes.update(id, { title: "New" })          → merges fields
      await recipes.remove(id)                             → deletes item
      recipes.onChange(({ action, id, value, author }) => { })  → real-time SSE

    ### File Uploads
      const result = await deplixo.upload(file)  → { url, filename, size }
      await deplixo.uploads.list()               → [{ filename, url, size }]
      await deplixo.uploads.delete(filename)

    Upload first, then store the URL in a collection entry:
      const photo = await deplixo.upload(fileInput.files[0]);
      await recipes.add({ title: "Pasta", photo: photo.url });
    Max 5MB per file. Do NOT use base64, data URLs, or FileReader.readAsDataURL().

    ### Identity
      deplixo.user  → { id, name } for the current visitor
      await deplixo.ensureIdentity()  → prompts for display name (multi-user apps only)
      Author info is included in collection .list() and .onChange() results.
      NOTE: You MUST always pass the `personal` option when creating a collection:
      - Personal apps: `deplixo.db.collection("state", { personal: true })`
      - Multi-user apps: `deplixo.db.collection("recipes", { personal: false })`

    ### Proxy (call external APIs with server-side secrets)
      const data = await deplixo.proxy(url, { method, headers, body })
      → { status: 200, body: { ... } }
    Secrets are resolved server-side: use ${SECRET_NAME} in headers or body.
    The app owner must configure secrets and allowed domains in the dashboard.
    Example:
      const weather = await deplixo.proxy(
        "https://api.weather.gov/gridpoints/OKX/33,37/forecast",
        { headers: { "Authorization": "Bearer ${WEATHER_KEY}" } }
      );
    NEVER embed API keys in HTML/JS source. Use deplixo.proxy() with secrets.

    ### AI (platform-managed LLM access)
      const answer = await deplixo.ai.prompt("Generate 5 quiz questions")
      → "1. What is..."

      const result = await deplixo.ai.prompt({
        system: "You are a quiz master. Return JSON.",
        user: "Generate 5 questions about space",
        json: true
      })
      → { questions: [...] }

      // Streaming
      const stream = deplixo.ai.stream("Write a story about a robot");
      for await (const chunk of stream) {
        outputEl.textContent += chunk;
      }
    AI uses the app owner's credits (included with their tier). No API key
    needed — it just works. The app owner can configure the model tier (low,
    medium, high) and preferred provider in the dashboard.
    NEVER embed LLM API keys in source code. Use deplixo.ai.prompt() instead.

    ### IMPORTANT RULES
    - ALWAYS use deplixo.db.collection() for ANY persistent data — even for
      single-user apps. Users expect their data on all their devices (phone,
      desktop, tablet). localStorage does NOT sync across devices.
    - NEVER use localStorage. Always use deplixo.db.collection() instead.
      Collections sync across all devices and browsers in real-time via SSE.
    - NEVER use base64/data URLs for images — use deplixo.upload()
    - NEVER embed API keys in HTML/JS — use deplixo.proxy() with ${SECRET_NAME}
    - NEVER embed LLM API keys — use deplixo.ai.prompt() (uses platform credits)
    - Collections are shared across ALL visitors automatically
    - Real-time updates work via .onChange() — ALWAYS use it to re-render on changes
    - If the user's existing code uses localStorage, REWRITE it to use
      deplixo.db.collection() before deploying. Do not deploy localStorage code.

    ### Two patterns: Personal Apps vs Multi-User Apps

    CRITICAL: Choose the right pattern based on how many people use the app.
    You MUST always pass the `personal` option explicitly on every collection.

    **Personal app** (one person, multiple devices — tracker, journal, todo):
    - MUST pass `{ personal: true }`:
        `deplixo.db.collection("state", { personal: true })`
    - Use ONE shared record. All devices read and write the SAME record.
    - Do NOT filter by deplixo.user.id or author — visitor IDs are per-browser,
      so phone and desktop have DIFFERENT IDs even for the same person.
    - Do NOT use ensureIdentity or require a display name.
    - onChange fires on ALL devices, all re-render the same data.

    **Multi-user app** (multiple people — chat, shared list, scoreboard):
    - MUST pass `{ personal: false }`:
        `deplixo.db.collection("recipes", { personal: false })`
    - Each person adds their own entries via .add() — author is tracked.
    - Use deplixo.user and author info to show who contributed what.
    - Identity modal will prompt for a display name on first write.
    - onChange fires for everyone, all re-render the full shared list.

    ### Example: Personal App — Progress Tracker
    One person across phone, tablet, desktop. All devices stay in sync.

      const store = deplixo.db.collection("state", { personal: true });
      let appState = {};
      let recordId = null;

      async function loadState() {
        const items = await store.list();
        if (items.length > 0) {
          recordId = items[0].id;
          appState = items[0].value;
        }
        render(appState);
      }

      async function saveState(newState) {
        appState = newState;
        if (recordId) await store.update(recordId, newState);
        else {
          const result = await store.add(newState);
          recordId = result.id;
        }
        render(appState);
      }

      // Any device saves → all other devices re-render automatically
      store.onChange(() => loadState());
      loadState();

    ### Example: Multi-User App — Shared Recipe Box
    Multiple people contribute and see each other's entries.

      const recipes = deplixo.db.collection("recipes", { personal: false });
      // Identity prompt happens automatically on first write (add/update/remove)

      async function loadRecipes() {
        const all = await recipes.list();
        renderRecipes(all);  // each item: { id, value, author: { id, name } }
      }
      async function addRecipe(title, ingredients, photoFile) {
        const photo = await deplixo.upload(photoFile);
        await recipes.add({ title, ingredients, photo: photo.url });
      }
      recipes.onChange(() => loadRecipes());
      loadRecipes();

    Args:
        code: HTML code for single-file apps. Mutually exclusive with `files`.
        files: Dict of {path: content} for multi-file apps. Must include
               "index.html". Example: {"index.html": "...", "style.css": "...",
               "app.js": "..."}. Files are served at their paths relative to
               the app URL (e.g. deplixo.com/abcd-efgh/style.css).
        title: A short title for the app
        slug: Optional URL slug for a named app URL (requires an account)
        remixed_from: Optional app ID of the app this was remixed from (e.g. abcd-efgh)
        app_id: Hash ID from a previous deploy to update an existing app
        claim_token: Claim token from a previous deploy, required when updating
                     an unclaimed app
    """
    if not code and not files:
        return "Error: Either 'code' or 'files' must be provided."
    if files and "index.html" not in files:
        return "Error: 'files' must include 'index.html'."

    payload: dict = {"title": title}
    if files:
        payload["files"] = files
    else:
        payload["code"] = code
    if slug:
        payload["slug"] = slug
    if remixed_from:
        payload["remixed_from"] = remixed_from
    if app_id:
        payload["app_id"] = app_id
    if claim_token:
        payload["claim_token"] = claim_token

    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(
            f"{DEPLIXO_API_URL}/api/v1/deploy",
            json=payload,
        )

    if response.status_code == 200:
        data = response.json()
        url = data.get("url", "")
        hash_id = data.get("hash_id", "")
        updated = data.get("updated", False)
        resp_claim_token = data.get("claim_token", "")
        claim_url = data.get("claim_url")

        suggestions = data.get("suggestions")

        if updated:
            parts = [
                f"App updated! Live at: {url}",
            ]
            if claim_url:
                parts.extend([
                    "",
                    "APP DURATION: This app is still UNCLAIMED and will expire "
                    "in 24 hours. Claiming is free and extends it to 7 days. "
                    "Paid plans (Personal/Pro) keep apps permanently.",
                    f"Claim link: {claim_url}",
                    "",
                    "IMPORTANT: You MUST tell the user how long their app will "
                    "last and show them BOTH the live URL and the claim link. "
                    "Without the claim link, they will lose access permanently.",
                ])
            parts.append("")
            update_line = f'To update again, pass app_id="{hash_id}"'
            if resp_claim_token:
                update_line += f' and claim_token="{resp_claim_token}".'
            else:
                update_line += "."
            parts.append(update_line)
            if suggestions:
                parts.extend(_format_suggestions(suggestions))
            return "\n".join(parts)

        # New deploy
        parts = [
            f"App deployed! Live at: {url}",
            "",
            "APP DURATION: This app will expire in 24 hours unless claimed. "
            "Claiming is free and extends it to 7 days. "
            "Paid plans (Personal/Pro) keep apps permanently.",
        ]
        if claim_url:
            parts.extend([
                "",
                f"Claim link: {claim_url}",
                "Claiming lets the user name it, get a custom URL "
                "(deplixo.com/you/my-app), manage it from their dashboard, "
                "and track visitors.",
                "",
                "IMPORTANT: You MUST tell the user how long their app will last "
                "and show them BOTH the live URL and the claim link. The claim "
                "link is the ONLY way for the user to save and manage this app. "
                "If you do not show it, they will lose access permanently.",
            ])
        if resp_claim_token:
            parts.extend([
                "",
                f'To update this app in the current conversation, pass app_id="{hash_id}" '
                f'and claim_token="{resp_claim_token}".',
            ])
        if suggestions:
            parts.extend(_format_suggestions(suggestions))
        return "\n".join(parts)
    else:
        error_text = response.text[:5000] if len(response.text) > 5000 else response.text
        return f"Deployment failed (HTTP {response.status_code}): {error_text}"


def main():
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
