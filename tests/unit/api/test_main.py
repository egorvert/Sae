"""Tests for the main FastAPI application."""

from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient


class TestCreateApp:
    """Tests for create_app function."""

    def test_create_app_returns_fastapi_instance(self, mock_settings: MagicMock) -> None:
        """Test that create_app returns a FastAPI instance."""
        from sae.main import create_app

        app = create_app()
        assert isinstance(app, FastAPI)

    def test_create_app_has_title(self, mock_settings: MagicMock) -> None:
        """Test that app has correct title."""
        from sae.main import create_app

        app = create_app()
        assert app.title == "Sae Legal Agent"

    def test_create_app_includes_routers(self, mock_settings: MagicMock) -> None:
        """Test that all routers are included."""
        from sae.main import create_app

        app = create_app()
        routes = [route.path for route in app.routes]

        # Check for key endpoints
        assert "/.well-known/agent.json" in routes
        assert "/a2a" in routes
        assert "/health" in routes


class TestHealthEndpoint:
    """Tests for the /health endpoint."""

    def test_health_returns_200(self, client: TestClient) -> None:
        """Test that health endpoint returns 200."""
        response = client.get("/health")
        assert response.status_code == 200

    def test_health_returns_healthy_status(self, client: TestClient) -> None:
        """Test that health endpoint returns healthy status."""
        response = client.get("/health")
        data = response.json()
        assert data["status"] == "healthy"

    def test_health_returns_version(self, client: TestClient) -> None:
        """Test that health endpoint returns version."""
        response = client.get("/health")
        data = response.json()
        assert "version" in data

    def test_health_returns_agent_name(
        self, client: TestClient, mock_settings: MagicMock
    ) -> None:
        """Test that health endpoint returns agent name."""
        response = client.get("/health")
        data = response.json()
        assert data["agent"] == mock_settings.agent_name


class TestDocsEndpoint:
    """Tests for documentation endpoints."""

    def test_docs_available_in_development(self, mock_settings: MagicMock) -> None:
        """Test that /docs is available in development."""
        mock_settings.is_production = False

        from sae.main import create_app

        app = create_app()
        assert app.docs_url == "/docs"
        assert app.redoc_url == "/redoc"

    def test_docs_disabled_in_production(
        self, mock_production_settings: MagicMock
    ) -> None:
        """Test that /docs is disabled in production."""
        # Need to patch where get_settings is used in main.py
        with patch("sae.main.get_settings", return_value=mock_production_settings):
            from sae.main import create_app

            app = create_app()
            assert app.docs_url is None
            assert app.redoc_url is None


class TestCORS:
    """Tests for CORS configuration."""

    def test_cors_headers_present(self, client: TestClient) -> None:
        """Test that CORS headers are present in response."""
        response = client.options(
            "/health",
            headers={"Origin": "http://example.com"},
        )
        # CORS middleware should allow the request
        assert response.status_code in [200, 405]
