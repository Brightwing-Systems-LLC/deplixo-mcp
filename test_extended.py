"""Extended tests for server.py — covering uncovered tools and error paths."""
import pytest
import httpx
from unittest.mock import AsyncMock, MagicMock, patch

import server
from server import (
    deplixo_capabilities,
    deplixo_deploy,
    deplixo_enhance,
    deplixo_query,
    deplixo_read_source,
)


@pytest.fixture(autouse=True)
def _pre_populate_registry_cache():
    """Pre-populate the registry cache with minimal data so tests don't make real HTTP calls."""
    server._registry_cache = [
        {
            "id": "collections", "namespace": "deplixo.db.collection", "name": "Collections",
            "category": "data-storage", "description": {"short": "Persistent data"},
            "methods": [], "icon": "", "tags": [], "related": [], "deploy_flags": [],
            "credits": None, "snippet": "await deplixo.ready;\nconst col = deplixo.db.collection('items', { personal: true });",
            "anti_patterns": "NEVER omit { personal: true/false }",
            "contrast": {"feature": "Persistent data", "without": "Data disappears when they close the tab", "with": "Data persists forever and syncs across devices"},
            "sdk_feature_label": "Collections", "sdk_feature_pattern": "deplixo.db.collection",
            "detection": {}, "production_features": [],
        },
        {
            "id": "ai", "namespace": "deplixo.ai", "name": "AI",
            "category": "ai", "description": {"short": "AI/LLM calls"},
            "methods": [], "icon": "", "tags": [], "related": [], "deploy_flags": [],
            "credits": None, "snippet": "const result = await deplixo.ai.prompt({ system: '...', user: input, json: true });",
            "anti_patterns": "NEVER use a bare string prompt for structured output",
            "contrast": {"feature": "AI-powered content", "without": "Static hardcoded content", "with": "AI generates content on demand"},
            "sdk_feature_label": "AI", "sdk_feature_pattern": "deplixo.ai.prompt",
            "detection": {}, "production_features": [],
        },
    ]
    yield
    server._registry_cache = None


# ---------- deplixo_deploy — error paths ----------

class TestDeployErrors:
    @pytest.mark.asyncio
    async def test_connect_error(self):
        with patch("httpx.AsyncClient") as MockClient:
            client_instance = AsyncMock()
            client_instance.post.side_effect = httpx.ConnectError("refused")
            client_instance.__aenter__ = AsyncMock(return_value=client_instance)
            client_instance.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value = client_instance
            result = await deplixo_deploy(code="<html></html>")
            assert "Could not connect" in result

    @pytest.mark.asyncio
    async def test_generic_http_error(self):
        with patch("httpx.AsyncClient") as MockClient:
            client_instance = AsyncMock()
            client_instance.post.side_effect = httpx.HTTPError("something broke")
            client_instance.__aenter__ = AsyncMock(return_value=client_instance)
            client_instance.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value = client_instance
            result = await deplixo_deploy(code="<html></html>")
            assert "HTTP request failed" in result


class TestDeployResponseFormatting:
    @pytest.mark.asyncio
    async def test_suggestions_in_new_deploy(self):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "url": "https://deplixo.com/abcd-efgh",
            "hash_id": "abcd-efgh",
            "claim_token": "tok_123",
            "claim_url": "https://deplixo.com/claim/tok_123",
            "updated": False,
            "suggestions": {
                "title": "My App",
                "features": ["Add a form", "Add charts"],
            },
            "production_features": [
                {"feature": "Real-time data sync", "test": "Open on two devices"},
                {"feature": "AI-powered content", "test": "Try the AI prompt"},
            ],
            "asset_warnings": ["Image too large: hero.jpg"],
        }
        with patch("httpx.AsyncClient") as MockClient:
            client_instance = AsyncMock()
            client_instance.post = AsyncMock(return_value=mock_response)
            client_instance.__aenter__ = AsyncMock(return_value=client_instance)
            client_instance.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value = client_instance
            result = await deplixo_deploy(code="<html></html>")
            assert "activation link" in result.lower()
            assert "claim/tok_123" in result

    @pytest.mark.asyncio
    async def test_update_with_asset_warnings(self):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "url": "https://deplixo.com/abcd-efgh",
            "hash_id": "abcd-efgh",
            "claim_token": "tok_123",
            "updated": True,
            "asset_warnings": ["Failed to download: bad.jpg"],
        }
        with patch("httpx.AsyncClient") as MockClient:
            client_instance = AsyncMock()
            client_instance.post = AsyncMock(return_value=mock_response)
            client_instance.__aenter__ = AsyncMock(return_value=client_instance)
            client_instance.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value = client_instance
            result = await deplixo_deploy(code="<html></html>", app_id="abcd-efgh", claim_token="tok_123")
            assert "Asset warnings" in result
            assert "bad.jpg" in result


# ---------- deplixo_read_source — error paths ----------

class TestReadSourceErrors:
    @pytest.mark.asyncio
    async def test_invalid_url(self):
        result = await deplixo_read_source("https://google.com/not-deplixo")
        assert "Error" in result
        assert "parse" in result.lower()

    @pytest.mark.asyncio
    async def test_edit_link_resolution_error(self):
        mock_resolve = MagicMock()
        mock_resolve.status_code = 404
        mock_resolve.json.return_value = {}

        with patch("httpx.AsyncClient") as MockClient:
            client_instance = AsyncMock()
            client_instance.get = AsyncMock(return_value=mock_resolve)
            client_instance.__aenter__ = AsyncMock(return_value=client_instance)
            client_instance.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value = client_instance
            result = await deplixo_read_source("https://deplixo.com/edit/" + "a" * 64)
            assert "Error" in result
            assert "404" in result

    @pytest.mark.asyncio
    async def test_timeout(self):
        with patch("httpx.AsyncClient") as MockClient:
            client_instance = AsyncMock()
            client_instance.get.side_effect = httpx.TimeoutException("timeout")
            client_instance.__aenter__ = AsyncMock(return_value=client_instance)
            client_instance.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value = client_instance
            result = await deplixo_read_source("https://deplixo.com/abcd-efgh")
            assert "timed out" in result.lower()

    @pytest.mark.asyncio
    async def test_generic_exception(self):
        with patch("httpx.AsyncClient") as MockClient:
            client_instance = AsyncMock()
            client_instance.get.side_effect = RuntimeError("unexpected")
            client_instance.__aenter__ = AsyncMock(return_value=client_instance)
            client_instance.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value = client_instance
            result = await deplixo_read_source("https://deplixo.com/abcd-efgh")
            assert "Error reading source" in result


# ---------- deplixo_enhance ----------

class TestEnhance:
    @pytest.mark.asyncio
    async def test_api_error_fallback(self):
        mock_response = MagicMock()
        mock_response.status_code = 500
        with patch("httpx.AsyncClient") as MockClient:
            client_instance = AsyncMock()
            client_instance.post = AsyncMock(return_value=mock_response)
            client_instance.__aenter__ = AsyncMock(return_value=client_instance)
            client_instance.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value = client_instance
            result = await deplixo_enhance("a todo app")
            assert "Enhancement Analysis" in result
            assert "deplixo.db.collection" in result

    @pytest.mark.asyncio
    async def test_generic_exception(self):
        with patch("httpx.AsyncClient") as MockClient:
            client_instance = AsyncMock()
            client_instance.post.side_effect = RuntimeError("network error")
            client_instance.__aenter__ = AsyncMock(return_value=client_instance)
            client_instance.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value = client_instance
            result = await deplixo_enhance("a quiz app")
            assert "unavailable" in result.lower()

    @pytest.mark.asyncio
    async def test_success(self):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "pattern": "personal",
            "recommended_primitives": ["deplixo.db.collection", "deplixo.ai"],
            "clarifying_questions": ["Should this be just for you?"],
        }
        with patch("httpx.AsyncClient") as MockClient:
            client_instance = AsyncMock()
            client_instance.post = AsyncMock(return_value=mock_response)
            client_instance.__aenter__ = AsyncMock(return_value=client_instance)
            client_instance.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value = client_instance
            result = await deplixo_enhance("a recipe app")
            assert "Enhancement Analysis" in result
            assert "Persistent data" in result
            assert "AI" in result  # contrast comes from registry


# ---------- deplixo_capabilities ----------

class TestCapabilities:
    @pytest.mark.asyncio
    async def test_returns_markdown(self):
        result = await deplixo_capabilities()
        assert "Deplixo Platform Capabilities" in result
        assert "Collections" in result  # from registry fixture
        assert "deplixo_deploy" in result


# ---------- deplixo_query ----------

class TestQuery:
    @pytest.mark.asyncio
    async def test_no_collection_or_sql(self):
        result = await deplixo_query(app_id="abcd-efgh", claim_token="tok_123")
        assert "Error" in result

    @pytest.mark.asyncio
    async def test_forbidden(self):
        mock_response = MagicMock()
        mock_response.status_code = 403
        with patch("httpx.AsyncClient") as MockClient:
            client_instance = AsyncMock()
            client_instance.post = AsyncMock(return_value=mock_response)
            client_instance.__aenter__ = AsyncMock(return_value=client_instance)
            client_instance.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value = client_instance
            result = await deplixo_query(app_id="abcd-efgh", claim_token="bad", collection="items")
            assert "Invalid activation token" in result

    @pytest.mark.asyncio
    async def test_collection_success(self):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "app_id": "abcd-efgh",
            "collection": "items",
            "entries": [
                {"id": "1", "value": {"name": "Test"}, "author": {"name": "Alice"}},
            ],
            "total": 1,
        }
        with patch("httpx.AsyncClient") as MockClient:
            client_instance = AsyncMock()
            client_instance.post = AsyncMock(return_value=mock_response)
            client_instance.__aenter__ = AsyncMock(return_value=client_instance)
            client_instance.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value = client_instance
            result = await deplixo_query(
                app_id="abcd-efgh", claim_token="tok_123", collection="items"
            )
            assert "items" in result
            assert "Alice" in result

    @pytest.mark.asyncio
    async def test_sql_success(self):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "app_id": "abcd-efgh",
            "columns": ["num"],
            "rows": [{"num": 42}],
            "count": 1,
        }
        with patch("httpx.AsyncClient") as MockClient:
            client_instance = AsyncMock()
            client_instance.post = AsyncMock(return_value=mock_response)
            client_instance.__aenter__ = AsyncMock(return_value=client_instance)
            client_instance.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value = client_instance
            result = await deplixo_query(
                app_id="abcd-efgh", claim_token="tok_123", sql="SELECT 42 as num"
            )
            assert "42" in result

    @pytest.mark.asyncio
    async def test_generic_error(self):
        with patch("httpx.AsyncClient") as MockClient:
            client_instance = AsyncMock()
            client_instance.post.side_effect = RuntimeError("oops")
            client_instance.__aenter__ = AsyncMock(return_value=client_instance)
            client_instance.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value = client_instance
            result = await deplixo_query(
                app_id="abcd-efgh", claim_token="tok_123", collection="x"
            )
            assert "failed" in result.lower()

    @pytest.mark.asyncio
    async def test_non_200_error(self):
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.headers = {"content-type": "application/json"}
        mock_response.json.return_value = {"error": "Internal error"}
        mock_response.text = "Internal error"
        with patch("httpx.AsyncClient") as MockClient:
            client_instance = AsyncMock()
            client_instance.post = AsyncMock(return_value=mock_response)
            client_instance.__aenter__ = AsyncMock(return_value=client_instance)
            client_instance.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value = client_instance
            result = await deplixo_query(
                app_id="abcd-efgh", claim_token="tok_123", collection="x"
            )
            assert "failed" in result.lower()


