"""Tests for merge_files parameter in the MCP deploy tool."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from server import deplixo_deploy


def _mock_api_success(return_data):
    """Helper to create a mock httpx client that returns success."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = return_data

    mock_client = AsyncMock()
    mock_client.post.return_value = mock_response
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    return mock_client


@pytest.mark.asyncio
async def test_merge_files_included_in_payload():
    """merge_files=True is passed to the API payload."""
    mock_client = _mock_api_success({
        "url": "https://deplixo.com/abcd-efgh",
        "hash_id": "abcd-efgh",
        "updated": True,
    })

    with patch("server.httpx.AsyncClient") as mock_cls:
        mock_cls.return_value = mock_client
        await deplixo_deploy(
            files={"app.js": "console.log('chunk 2');"},
            app_id="abcd-efgh",
            claim_token="tok_123",
            merge_files=True,
        )

    payload = mock_client.post.call_args.kwargs.get("json") or mock_client.post.call_args[1].get("json")
    assert payload["merge_files"] is True
    assert payload["app_id"] == "abcd-efgh"
    assert payload["claim_token"] == "tok_123"
    assert payload["files"] == {"app.js": "console.log('chunk 2');"}


@pytest.mark.asyncio
async def test_merge_files_false_not_in_payload():
    """merge_files=False (default) is not included in the payload."""
    mock_client = _mock_api_success({
        "url": "https://deplixo.com/abcd-efgh",
        "hash_id": "abcd-efgh",
    })

    with patch("server.httpx.AsyncClient") as mock_cls:
        mock_cls.return_value = mock_client
        await deplixo_deploy(code="<h1>Hello</h1>")

    payload = mock_client.post.call_args.kwargs.get("json") or mock_client.post.call_args[1].get("json")
    assert "merge_files" not in payload


@pytest.mark.asyncio
async def test_merge_files_without_index_html_allowed():
    """merge_files=True allows files dict without index.html (client-side)."""
    mock_client = _mock_api_success({
        "url": "https://deplixo.com/abcd-efgh",
        "hash_id": "abcd-efgh",
        "updated": True,
    })

    with patch("server.httpx.AsyncClient") as mock_cls:
        mock_cls.return_value = mock_client
        # This should NOT hit the client-side "index.html required" check
        # because merge_files on an update doesn't need index.html
        result = await deplixo_deploy(
            files={"style.css": "body {}"},
            app_id="abcd-efgh",
            claim_token="tok_123",
            merge_files=True,
        )

    # Should have called the API (not returned early with error)
    assert mock_client.post.called
    assert "App updated" in result


@pytest.mark.asyncio
async def test_merge_files_without_app_id_still_validates_index():
    """merge_files on first deploy (no app_id) still requires index.html."""
    result = await deplixo_deploy(
        files={"app.js": "console.log('hi')"},
        merge_files=True,
    )
    assert "Error" in result
    assert "index.html" in result


@pytest.mark.asyncio
async def test_merge_files_chunked_workflow():
    """Simulate the full chunked deploy workflow."""
    # Chunk 1: initial deploy
    mock_client_1 = _mock_api_success({
        "url": "https://deplixo.com/abcd-efgh",
        "hash_id": "abcd-efgh",
        "claim_token": "tok_123",
        "claim_url": "https://deplixo.com/claim/abc",
    })

    with patch("server.httpx.AsyncClient") as mock_cls:
        mock_cls.return_value = mock_client_1
        result1 = await deplixo_deploy(
            files={"index.html": "<h1>App</h1>", "style.css": "body {}"},
            title="Chunked App",
        )

    assert "abcd-efgh" in result1
    payload1 = mock_client_1.post.call_args.kwargs.get("json") or mock_client_1.post.call_args[1].get("json")
    assert "merge_files" not in payload1

    # Chunk 2: add JS with merge
    mock_client_2 = _mock_api_success({
        "url": "https://deplixo.com/abcd-efgh",
        "hash_id": "abcd-efgh",
        "updated": True,
        "claim_token": "tok_123",
        "claim_url": "https://deplixo.com/claim/abc",
    })

    with patch("server.httpx.AsyncClient") as mock_cls:
        mock_cls.return_value = mock_client_2
        result2 = await deplixo_deploy(
            files={"app.js": "function init() {}"},
            app_id="abcd-efgh",
            claim_token="tok_123",
            merge_files=True,
        )

    assert "updated" in result2.lower()
    payload2 = mock_client_2.post.call_args.kwargs.get("json") or mock_client_2.post.call_args[1].get("json")
    assert payload2["merge_files"] is True
    assert payload2["files"] == {"app.js": "function init() {}"}
    assert "index.html" not in payload2.get("files", {})


@pytest.mark.asyncio
async def test_merge_files_with_code_param():
    """merge_files works with code param (updates main HTML)."""
    mock_client = _mock_api_success({
        "url": "https://deplixo.com/abcd-efgh",
        "hash_id": "abcd-efgh",
        "updated": True,
    })

    with patch("server.httpx.AsyncClient") as mock_cls:
        mock_cls.return_value = mock_client
        await deplixo_deploy(
            code="<h1>Updated HTML</h1>",
            app_id="abcd-efgh",
            claim_token="tok_123",
            merge_files=True,
        )

    payload = mock_client.post.call_args.kwargs.get("json") or mock_client.post.call_args[1].get("json")
    assert payload["code"] == "<h1>Updated HTML</h1>"
    assert payload["merge_files"] is True


@pytest.mark.asyncio
async def test_merge_files_api_error_forwarded():
    """API errors during merge are forwarded to the user."""
    mock_response = MagicMock()
    mock_response.status_code = 400
    mock_response.text = "Total file size exceeds maximum (5MB for your tier)"

    mock_client = AsyncMock()
    mock_client.post.return_value = mock_response
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with patch("server.httpx.AsyncClient") as mock_cls:
        mock_cls.return_value = mock_client
        result = await deplixo_deploy(
            files={"huge.js": "x" * 1000},
            app_id="abcd-efgh",
            claim_token="tok_123",
            merge_files=True,
        )

    assert "Deployment failed" in result
    assert "400" in result


@pytest.mark.asyncio
async def test_merge_default_is_false():
    """Default value of merge_files is False."""
    import inspect
    sig = inspect.signature(deplixo_deploy)
    assert sig.parameters["merge_files"].default is False
