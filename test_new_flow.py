"""Tests for new MCP behavior: claim-link-only responses, expiry messaging, and read_source tool."""
import pytest
import httpx
from unittest.mock import AsyncMock, MagicMock, patch

import server
from server import deplixo_deploy, deplixo_read_source, mcp


@pytest.fixture(autouse=True)
def _pre_populate_registry_cache():
    """Pre-populate the registry cache with minimal data so tests don't make real HTTP calls."""
    server._registry_cache = [
        {
            "id": "collections", "namespace": "deplixo.db.collection", "name": "Collections",
            "category": "data-storage", "description": {"short": "Persistent data"},
            "methods": [], "icon": "", "tags": [], "related": [], "deploy_flags": [],
            "credits": None, "snippet": "", "anti_patterns": "",
            "contrast": {"feature": "Persistent data", "without": "Data disappears", "with": "Data persists"},
            "sdk_feature_label": "Collections", "sdk_feature_pattern": "deplixo.db.collection",
            "detection": {}, "production_features": [],
        },
    ]
    yield
    server._registry_cache = None


@pytest.mark.asyncio
async def test_new_deploy_returns_claim_link_only():
    """New deploy response contains the claim link but NOT 'Live at:' text."""
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

    assert "https://deplixo.com/claim/abc123" in result
    assert "Live at:" not in result


@pytest.mark.asyncio
async def test_new_deploy_mentions_10_min_expiry():
    """New deploy response says '10 minutes', not '24 hours'."""
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

        result = await deplixo_deploy(code="<h1>Hello</h1>")

    assert "1 hour" in result
    assert "24 hours" not in result


@pytest.mark.asyncio
async def test_update_deploy_does_not_show_live_url():
    """Update deploy says 'App updated!' but does NOT include 'Live at:'."""
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
            app_id="abcd-efgh",
            claim_token="tok_secret123",
        )

    assert "App updated" in result
    assert "Live at:" not in result


def test_read_source_tool_exists():
    """deplixo_read_source is registered as a tool on the MCP server."""
    tools = mcp._tool_manager._tools
    tool = tools.get("deplixo_read_source")
    assert tool is not None
    assert tool.annotations is not None
    assert tool.annotations.readOnlyHint is True


@pytest.mark.asyncio
async def test_read_source_with_app_url():
    """Reading source with an app URL calls the correct API endpoint."""
    mock_source_response = MagicMock()
    mock_source_response.status_code = 200
    mock_source_response.json.return_value = {
        "title": "My App",
        "hash_id": "abcd-efgh",
        "author": "someone",
        "description": "A test app",
        "code": "<h1>Hello World</h1>",
        "files": {},
    }

    with patch("server.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.get.return_value = mock_source_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        result = await deplixo_read_source(url="https://deplixo.com/abcd-efgh")

    # Verify the correct API endpoint was called
    call_args = mock_client.get.call_args
    assert "/api/v1/apps/abcd-efgh/source" in call_args[0][0]
    # No token param for regular app URLs
    assert "?token=" not in call_args[0][0]

    # Verify formatted output
    assert "My App" in result
    assert "<h1>Hello World</h1>" in result


@pytest.mark.asyncio
async def test_read_source_with_edit_link():
    """Reading source with an edit link resolves the token, then fetches source with it."""
    token = "a" * 64  # 64-char hex token

    # First call: resolve edit link -> returns hash_id
    mock_edit_response = MagicMock()
    mock_edit_response.status_code = 200
    mock_edit_response.json.return_value = {"hash_id": "wxyz-1234"}

    # Second call: fetch source with token
    mock_source_response = MagicMock()
    mock_source_response.status_code = 200
    mock_source_response.json.return_value = {
        "title": "Edit App",
        "hash_id": "wxyz-1234",
        "author": "editor",
        "description": "",
        "code": "<h1>Editable</h1>",
        "files": {},
    }

    with patch("server.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.get.side_effect = [mock_edit_response, mock_source_response]
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        result = await deplixo_read_source(url=f"https://deplixo.com/edit/{token}")

    # Should have made two GET requests
    assert mock_client.get.call_count == 2

    # First call: resolve edit token
    first_call = mock_client.get.call_args_list[0]
    assert f"/edit/{token}/" in first_call[0][0]

    # Second call: fetch source with token
    second_call = mock_client.get.call_args_list[1]
    assert "/api/v1/apps/wxyz-1234/source" in second_call[0][0]
    assert f"?token={token}" in second_call[0][0]

    # Response includes update instructions with the token
    assert 'app_id="wxyz-1234"' in result
    assert f'claim_token="{token}"' in result


@pytest.mark.asyncio
async def test_read_source_api_error():
    """A 404 from the source API returns an error message."""
    mock_response = MagicMock()
    mock_response.status_code = 404
    mock_response.text = "Not Found"

    with patch("server.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        result = await deplixo_read_source(url="https://deplixo.com/zzzz-zzzz")

    assert "Error" in result
    assert "404" in result


@pytest.mark.asyncio
async def test_deploy_tool_uses_claim_token():
    """Deploy tool passes claim_token (not edit_token) in the payload."""
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
            app_id="abcd-efgh",
            claim_token="tok_secret123",
        )

    call_kwargs = mock_client.post.call_args
    payload = call_kwargs.kwargs.get("json") or call_kwargs[1].get("json")
    assert "claim_token" in payload
    assert payload["claim_token"] == "tok_secret123"
    assert "edit_token" not in payload
