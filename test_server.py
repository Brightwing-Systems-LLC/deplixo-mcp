"""Tests for the Deplixo MCP server."""
import pytest
import httpx
from unittest.mock import AsyncMock, MagicMock, patch

from server import deplixo_deploy


@pytest.mark.asyncio
async def test_deploy_requires_code_or_files():
    result = await deplixo_deploy()
    assert "Error" in result
    assert "'code' or 'files'" in result


@pytest.mark.asyncio
async def test_deploy_files_requires_index_html():
    result = await deplixo_deploy(files={"app.js": "console.log('hi')"})
    assert "Error" in result
    assert "index.html" in result


@pytest.mark.asyncio
async def test_deploy_single_file_success():
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "url": "https://deplixo.com/abcd-efgh",
        "hash_id": "abcd-efgh",
        "claim_token": "tok_secret123",
        "claim_url": "https://deplixo.com/claim/abc123",
    }

    with patch("server.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        result = await deplixo_deploy(code="<h1>Hello</h1>", title="Test App")

    assert "App deployed" in result
    assert "deplixo.com/claim/abc123" in result
    assert "tok_secret123" in result
    assert "app_id=" in result
    assert "1 hour" in result
    # New deploys should NOT show the live app URL
    assert "Live at:" not in result


@pytest.mark.asyncio
async def test_deploy_multi_file_success():
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "url": "https://deplixo.com/wxyz-1234",
        "hash_id": "wxyz-1234",
    }

    with patch("server.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        result = await deplixo_deploy(
            files={"index.html": "<html></html>", "style.css": "body {}"}
        )

    assert "App deployed" in result


@pytest.mark.asyncio
async def test_deploy_api_error():
    mock_response = AsyncMock()
    mock_response.status_code = 500
    mock_response.text = "Internal Server Error"

    with patch("server.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        result = await deplixo_deploy(code="<h1>Hello</h1>")

    assert "Deployment failed" in result
    assert "500" in result


@pytest.mark.asyncio
async def test_deploy_error_response_truncated():
    mock_response = AsyncMock()
    mock_response.status_code = 500
    mock_response.text = "x" * 10000

    with patch("server.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        result = await deplixo_deploy(code="<h1>Hello</h1>")

    # Error text should be truncated to 5000 chars, not the full 10000
    assert len(result) < 6000


@pytest.mark.asyncio
async def test_deploy_timeout():
    with patch("server.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.post.side_effect = httpx.TimeoutException("Request timed out")
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        result = await deplixo_deploy(code="<h1>Hello</h1>")

    assert "Error" in result
    assert "timed out" in result


@pytest.mark.asyncio
async def test_deploy_update_existing_app():
    """Updating an existing app passes app_id and claim_token to the API."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "url": "https://deplixo.com/abcd-efgh",
        "hash_id": "abcd-efgh",
        "updated": True,
        "claim_token": "tok_secret123",
        "claim_url": "https://deplixo.com/claim/abc123",
    }

    with patch("server.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        result = await deplixo_deploy(
            code="<h1>Updated</h1>",
            title="Test App",
            app_id="abcd-efgh",
            claim_token="tok_secret123",
        )

    # Verify payload includes app_id and claim_token
    call_kwargs = mock_client.post.call_args
    payload = call_kwargs.kwargs.get("json") or call_kwargs[1].get("json")
    assert payload["app_id"] == "abcd-efgh"
    assert payload["claim_token"] == "tok_secret123"

    # Verify response shows update success
    assert "App updated" in result
    assert "1 hour" in result


@pytest.mark.asyncio
async def test_deploy_update_forbidden():
    """Updating without valid claim_token returns an error."""
    mock_response = MagicMock()
    mock_response.status_code = 403
    mock_response.text = "Valid claim_token required to update unclaimed app"

    with patch("server.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        result = await deplixo_deploy(
            code="<h1>Updated</h1>",
            app_id="abcd-efgh",
            claim_token="wrong_token",
        )

    assert "Deployment failed" in result
    assert "403" in result


@pytest.mark.asyncio
async def test_deploy_with_slug():
    """Slug is included in payload when provided."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "url": "https://deplixo.com/user/myapp",
        "hash_id": "abcd-efgh",
    }

    with patch("server.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        result = await deplixo_deploy(code="<h1>Hi</h1>", slug="myapp")

    payload = mock_client.post.call_args.kwargs.get("json") or mock_client.post.call_args[1].get("json")
    assert payload["slug"] == "myapp"


@pytest.mark.asyncio
async def test_deploy_with_remixed_from():
    """remixed_from is included in payload when provided."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "url": "https://deplixo.com/wxyz-abcd",
        "hash_id": "wxyz-abcd",
    }

    with patch("server.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        result = await deplixo_deploy(code="<h1>Remix</h1>", remixed_from="abcd-efgh")

    payload = mock_client.post.call_args.kwargs.get("json") or mock_client.post.call_args[1].get("json")
    assert payload["remixed_from"] == "abcd-efgh"


@pytest.mark.asyncio
async def test_deploy_no_claim_url():
    """Authenticated deploy (no claim_url in response) omits claim warning."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "url": "https://deplixo.com/user/myapp",
        "hash_id": "abcd-efgh",
    }

    with patch("server.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        result = await deplixo_deploy(code="<h1>Hi</h1>")

    # Authenticated deploy: no claim warning, just "App deployed!"
    assert "claim" not in result.lower()
    assert "App deployed" in result


def test_tool_annotations():
    """Verify tool annotations are set correctly for marketplace compliance."""
    from server import mcp

    tools = mcp._tool_manager._tools
    tool = tools.get("deplixo_deploy")
    assert tool is not None
    assert tool.annotations is not None
    assert tool.annotations.readOnlyHint is False
    assert tool.annotations.destructiveHint is False
    assert tool.annotations.openWorldHint is True
    assert tool.annotations.idempotentHint is False


def test_main_calls_run():
    """main() calls mcp.run(transport='stdio')."""
    with patch("server.mcp") as mock_mcp:
        from server import main
        main()
        mock_mcp.run.assert_called_once_with(transport="stdio")
