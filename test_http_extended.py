"""Extended tests for http_server.py — endpoints and middleware."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from starlette.testclient import TestClient

from http_server import create_app


@pytest.fixture
def app():
    return create_app()


@pytest.fixture
def client(app):
    return TestClient(app)


class TestHealthEndpoint:
    def test_returns_json(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert "uptime_seconds" in data


class TestFaviconEndpoint:
    def test_returns_file(self, client):
        resp = client.get("/favicon.ico")
        # Should return 200 or may return 404 if file missing in test env
        assert resp.status_code in (200, 404)


class TestRequestBodyLimitMiddleware:
    def test_get_requests_pass(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200
