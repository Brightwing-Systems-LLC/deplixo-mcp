"""Brightwing Launch MCP Server - Deploy AI apps instantly."""
import os
import httpx
from mcp.server.fastmcp import FastMCP

BRIGHTWING_API_URL = os.environ.get("BRIGHTWING_API_URL", "https://brightwing.app")

mcp = FastMCP(
    "Brightwing Launch",
    instructions=(
        "Use the brightwing_deploy tool to deploy web apps to Brightwing Launch. "
        "When the user asks you to deploy, share, host, or publish their app, "
        "use this tool. It returns a live URL instantly — no account required.\n\n"
        "IMPORTANT: Apps can be single-file (pass `code`) or multi-file (pass "
        "`files` dict with paths like index.html, style.css, app.js). "
        "Multi-file apps have each file served at its path under the app URL. "
        "For React apps, use CDN imports (unpkg.com/react, unpkg.com/react-dom, "
        "unpkg.com/@babel/standalone) with <script type=\"text/babel\"> — do NOT "
        "use npm, create-react-app, Vite, or any build tools. "
        "For Vue, Svelte, Three.js, etc., use their CDN builds the same way.\n\n"
        "Storage: Apps automatically get a persistent key-value store via "
        "window.brightwing.db (set/get/delete/list). localStorage also works — "
        "writes are automatically persisted to the server so data survives across "
        "sessions and devices. Do NOT use IndexedDB or other client-only storage "
        "if the user needs persistence."
    ),
)


@mcp.tool()
async def brightwing_deploy(
    code: str = "",
    files: dict[str, str] | None = None,
    title: str = "",
    slug: str = "",
    remixed_from: str = "",
) -> str:
    """Deploy a web app to Brightwing Launch and get a live URL.

    Apps can be single-file or multi-file. For single-file apps, pass the HTML
    as `code`. For multi-file apps (separate CSS, JS, assets), pass a `files`
    dict mapping file paths to content — must include "index.html".

    For React, Vue, or other frameworks: use CDN imports (e.g. unpkg.com/react@18,
    unpkg.com/react-dom@18, unpkg.com/@babel/standalone) — do NOT use npm or
    build tools. localStorage calls are automatically persisted to the server.

    Args:
        code: HTML code for single-file apps. Mutually exclusive with `files`.
        files: Dict of {path: content} for multi-file apps. Must include
               "index.html". Example: {"index.html": "...", "style.css": "...",
               "app.js": "..."}. Files are served at their paths relative to
               the app URL (e.g. brightwing.app/abc123/style.css).
        title: A short title for the app
        slug: Optional URL slug (requires an account with Personal tier or above)
        remixed_from: Optional hash_id of the app this was remixed from
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

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            f"{BRIGHTWING_API_URL}/api/v1/deploy",
            json=payload,
        )

    if response.status_code == 200:
        data = response.json()
        url = data.get("url", "")
        hash_id = data.get("hash_id", "")
        parts = [
            f"Your app is live at: {url}",
            f"Hash ID: {hash_id}",
            f"Source: {url.rstrip('/')}/source",
        ]
        claim_url = data.get("claim_url")
        if claim_url:
            parts.append(
                f"\nTo manage this app later, save this claim link: {claim_url}\n"
                f"(Visit the link and enter your email to attach the app to your account.)"
            )
        return "\n".join(parts)
    else:
        return f"Deployment failed (HTTP {response.status_code}): {response.text}"


def main():
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
