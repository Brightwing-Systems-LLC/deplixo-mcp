"""Deplixo MCP Server - Deploy AI apps instantly."""
import os
import httpx
from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations

DEPLIXO_API_URL = os.environ.get("DEPLIXO_API_URL", "https://deplixo.com")

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
        "Unclaimed apps expire after 14 days.\n\n"
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
      const recipes = deplixo.db.collection("recipes");
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
      Author info is included in collection .list() and .onChange() results.

    ### IMPORTANT RULES
    - ALWAYS use deplixo.db.collection() for ANY persistent data — even for
      single-user apps. Users expect their data on all their devices (phone,
      desktop, tablet). localStorage does NOT sync across devices.
    - NEVER use localStorage. Always use deplixo.db.collection() instead.
      Collections sync across all devices and browsers in real-time via SSE.
    - NEVER use base64/data URLs for images — use deplixo.upload()
    - Collections are shared across ALL visitors automatically
    - Real-time updates work via .onChange() — ALWAYS use it to re-render on changes
    - If the user's existing code uses localStorage, REWRITE it to use
      deplixo.db.collection() before deploying. Do not deploy localStorage code.

    ### Two patterns: Personal Apps vs Multi-User Apps

    CRITICAL: Choose the right pattern based on how many people use the app.

    **Personal app** (one person, multiple devices — tracker, journal, todo):
    - Use ONE shared record. All devices read and write the SAME record.
    - Do NOT filter by deplixo.user.id or author — visitor IDs are per-browser,
      so phone and desktop have DIFFERENT IDs even for the same person.
    - Do NOT use ensureIdentity or require a display name.
    - onChange fires on ALL devices, all re-render the same data.

    **Multi-user app** (multiple people — chat, shared list, scoreboard):
    - Each person adds their own entries via .add() — author is tracked.
    - Use deplixo.user and author info to show who contributed what.
    - Identity modal will prompt for a display name on first write.
    - onChange fires for everyone, all re-render the full shared list.

    ### Example: Personal App — Progress Tracker
    One person across phone, tablet, desktop. All devices stay in sync.

      const store = deplixo.db.collection("state");
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

      const recipes = deplixo.db.collection("recipes");
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

    async with httpx.AsyncClient(timeout=30.0) as client:
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

        if updated:
            parts = [
                f"App updated! Live at: {url}",
                "",
                f'To update again, pass app_id="{hash_id}"',
            ]
            if resp_claim_token:
                parts[-1] += f' and claim_token="{resp_claim_token}".'
            else:
                parts[-1] += "."
            return "\n".join(parts)

        # New deploy
        parts = [f"App deployed! Live at: {url}"]
        if claim_url:
            parts.extend([
                "",
                "Claim this app to:",
                "  - Name it and get a custom URL (deplixo.com/you/my-app)",
                "  - Manage it from your dashboard",
                "  - Track visitors",
                "  - Keep it permanently (unclaimed apps expire after 14 days)",
                f"Claim link: {claim_url}",
                "",
                "IMPORTANT: You MUST show the user BOTH links above — the live URL "
                "and the claim link. The claim link is the ONLY way for the user to "
                "save and manage this app. If you do not show it, they will lose "
                "access to their app permanently.",
            ])
        if resp_claim_token:
            parts.extend([
                "",
                f'To update this app in the current conversation, pass app_id="{hash_id}" '
                f'and claim_token="{resp_claim_token}".',
            ])
        return "\n".join(parts)
    else:
        error_text = response.text[:5000] if len(response.text) > 5000 else response.text
        return f"Deployment failed (HTTP {response.status_code}): {error_text}"


def main():
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
