"""Brightwing Launch MCP Server - Deploy AI apps and publish blog posts."""
import os
import httpx
from mcp.server.fastmcp import FastMCP

BRIGHTWING_API_URL = os.environ.get("BRIGHTWING_API_URL", "https://brightwing.app")
BRIGHTWING_API_KEY = os.environ.get("BRIGHTWING_API_KEY", "")

mcp = FastMCP(
    "Brightwing Launch",
    instructions=(
        "Use the brightwing_deploy tool to deploy web apps to Brightwing Launch. "
        "When the user asks you to deploy, share, host, or publish their app, "
        "use this tool. It accepts HTML/JS/CSS code and returns a live URL. "
        "Use brightwing_blog_publish to publish blog posts from markdown."
    ),
)


@mcp.tool()
async def brightwing_deploy(
    code: str,
    title: str = "",
    slug: str = "",
    remixed_from: str = "",
) -> str:
    """Deploy a web app to Brightwing Launch and get a live URL.

    Args:
        code: The complete HTML/JS/CSS code of the app
        title: A short title for the app
        slug: Optional URL slug (requires Personal tier or above)
        remixed_from: Optional hash_id of the app this was remixed from
    """
    if not BRIGHTWING_API_KEY:
        return "Error: BRIGHTWING_API_KEY environment variable not set. Get your API key at https://brightwing.app/dashboard/api-key/"

    payload = {"code": code, "title": title}
    if slug:
        payload["slug"] = slug
    if remixed_from:
        payload["remixed_from"] = remixed_from

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            f"{BRIGHTWING_API_URL}/api/v1/deploy",
            json=payload,
            headers={"Authorization": f"Bearer {BRIGHTWING_API_KEY}"},
        )

    if response.status_code == 200:
        data = response.json()
        url = data.get("url", "")
        hash_id = data.get("hash_id", "")
        return (
            f"Your app is live at: {url}\n\n"
            f"Hash ID: {hash_id}\n"
            f"Source: {url.rstrip('/')}source\n"
            f"Dashboard: https://brightwing.app/dashboard/apps/{hash_id}/"
        )
    else:
        return f"Deployment failed (HTTP {response.status_code}): {response.text}"


@mcp.tool()
async def brightwing_blog_publish(
    title: str,
    markdown: str,
    slug: str = "",
    excerpt: str = "",
) -> str:
    """Publish a blog post to Brightwing Launch.

    Args:
        title: The blog post title
        markdown: The blog post content in markdown format
        slug: Optional URL slug. Auto-generated from title if omitted.
        excerpt: Optional short excerpt for the blog index and SEO.
    """
    if not BRIGHTWING_API_KEY:
        return "Error: BRIGHTWING_API_KEY environment variable not set. Get your API key at https://brightwing.app/dashboard/api-key/"

    payload = {"title": title, "markdown": markdown}
    if slug:
        payload["slug"] = slug
    if excerpt:
        payload["excerpt"] = excerpt

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            f"{BRIGHTWING_API_URL}/api/v1/blog",
            json=payload,
            headers={"Authorization": f"Bearer {BRIGHTWING_API_KEY}"},
        )

    if response.status_code == 200:
        data = response.json()
        url = data.get("url", "")
        return f"Blog post published: {url}\n\nTitle: {data.get('title', '')}"
    else:
        return f"Publishing failed (HTTP {response.status_code}): {response.text}"


def main():
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
