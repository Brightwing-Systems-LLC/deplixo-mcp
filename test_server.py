"""Tests for the Brightwing Launch MCP server."""
import pytest
import httpx
from unittest.mock import AsyncMock, MagicMock, patch

from server import brightwing_deploy


@pytest.mark.asyncio
async def test_deploy_requires_code_or_files():
    result = await brightwing_deploy()
    assert "Error" in result
    assert "'code' or 'files'" in result


@pytest.mark.asyncio
async def test_deploy_files_requires_index_html():
    result = await brightwing_deploy(files={"app.js": "console.log('hi')"})
    assert "Error" in result
    assert "index.html" in result


@pytest.mark.asyncio
async def test_deploy_single_file_success():
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "url": "https://brightwing.app/abcd-efgh",
        "hash_id": "abcd-efgh",
        "claim_url": "https://brightwing.app/claim/abc123",
    }

    with patch("server.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        result = await brightwing_deploy(code="<h1>Hello</h1>", title="Test App")

    assert "https://brightwing.app/abcd-efgh" in result
    assert "abcd-efgh" in result
    assert "claim" in result.lower()


@pytest.mark.asyncio
async def test_deploy_multi_file_success():
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "url": "https://brightwing.app/wxyz-1234",
        "hash_id": "wxyz-1234",
    }

    with patch("server.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        result = await brightwing_deploy(
            files={"index.html": "<html></html>", "style.css": "body {}"}
        )

    assert "https://brightwing.app/wxyz-1234" in result


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

        result = await brightwing_deploy(code="<h1>Hello</h1>")

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

        result = await brightwing_deploy(code="<h1>Hello</h1>")

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

        with pytest.raises(httpx.TimeoutException):
            await brightwing_deploy(code="<h1>Hello</h1>")


def test_tool_annotations():
    """Verify tool annotations are set correctly for marketplace compliance."""
    from server import mcp

    tools = mcp._tool_manager._tools
    tool = tools.get("brightwing_deploy")
    assert tool is not None
    assert tool.annotations is not None
    assert tool.annotations.readOnlyHint is False
    assert tool.annotations.destructiveHint is False
    assert tool.annotations.openWorldHint is True
    assert tool.annotations.idempotentHint is False
