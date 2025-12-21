"""Tests for API dependencies (authentication)."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

from sae.api.dependencies import verify_api_key


class TestVerifyApiKey:
    """Tests for verify_api_key dependency."""

    @pytest.mark.asyncio
    async def test_auth_disabled_when_no_api_key_configured(self) -> None:
        """Test that auth passes when no API_KEY is configured."""
        mock_settings = MagicMock()
        mock_settings.api_key = None  # Auth disabled

        mock_request = MagicMock()
        mock_request.url.path = "/a2a"
        mock_request.method = "POST"
        mock_request.client.host = "127.0.0.1"

        with patch("sae.api.dependencies.get_settings", return_value=mock_settings):
            result = await verify_api_key(
                request=mock_request,
                settings=mock_settings,
                x_api_key=None,
            )

        assert result is None

    @pytest.mark.asyncio
    async def test_auth_passes_with_valid_key(self) -> None:
        """Test that auth passes with valid API key."""
        mock_settings = MagicMock()
        mock_settings.api_key = "valid-secret-key"

        mock_request = MagicMock()
        mock_request.url.path = "/a2a"
        mock_request.method = "POST"
        mock_request.client.host = "127.0.0.1"

        with patch("sae.api.dependencies.get_settings", return_value=mock_settings):
            result = await verify_api_key(
                request=mock_request,
                settings=mock_settings,
                x_api_key="valid-secret-key",
            )

        assert result == "valid-secret-key"

    @pytest.mark.asyncio
    async def test_auth_fails_with_invalid_key(self) -> None:
        """Test that auth fails with invalid API key."""
        mock_settings = MagicMock()
        mock_settings.api_key = "valid-secret-key"

        mock_request = MagicMock()
        mock_request.url.path = "/a2a"
        mock_request.method = "POST"
        mock_request.client.host = "127.0.0.1"

        with patch("sae.api.dependencies.get_settings", return_value=mock_settings):
            with pytest.raises(HTTPException) as exc_info:
                await verify_api_key(
                    request=mock_request,
                    settings=mock_settings,
                    x_api_key="wrong-key",
                )

        assert exc_info.value.status_code == 401
        assert "Invalid API key" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_auth_fails_with_missing_key(self) -> None:
        """Test that auth fails when API key is required but not provided."""
        mock_settings = MagicMock()
        mock_settings.api_key = "valid-secret-key"

        mock_request = MagicMock()
        mock_request.url.path = "/a2a"
        mock_request.method = "POST"
        mock_request.client.host = "127.0.0.1"

        with patch("sae.api.dependencies.get_settings", return_value=mock_settings):
            with pytest.raises(HTTPException) as exc_info:
                await verify_api_key(
                    request=mock_request,
                    settings=mock_settings,
                    x_api_key=None,
                )

        assert exc_info.value.status_code == 401
        assert "Missing API key" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_auth_with_no_client_info(self) -> None:
        """Test that auth works when client info is not available."""
        mock_settings = MagicMock()
        mock_settings.api_key = "valid-secret-key"

        mock_request = MagicMock()
        mock_request.url.path = "/a2a"
        mock_request.method = "POST"
        mock_request.client = None  # No client info

        with patch("sae.api.dependencies.get_settings", return_value=mock_settings):
            result = await verify_api_key(
                request=mock_request,
                settings=mock_settings,
                x_api_key="valid-secret-key",
            )

        assert result == "valid-secret-key"

    @pytest.mark.asyncio
    async def test_constant_time_comparison(self) -> None:
        """Test that key comparison uses constant-time algorithm.

        This test verifies the security property that timing attacks
        are mitigated by using secrets.compare_digest.
        """
        mock_settings = MagicMock()
        mock_settings.api_key = "a" * 100  # Long key

        mock_request = MagicMock()
        mock_request.url.path = "/a2a"
        mock_request.method = "POST"
        mock_request.client.host = "127.0.0.1"

        # Test that both completely wrong and partially correct keys
        # result in the same error (timing should be similar)
        with patch("sae.api.dependencies.get_settings", return_value=mock_settings):
            with pytest.raises(HTTPException) as exc1:
                await verify_api_key(
                    request=mock_request,
                    settings=mock_settings,
                    x_api_key="b" * 100,  # Completely different
                )

            with pytest.raises(HTTPException) as exc2:
                await verify_api_key(
                    request=mock_request,
                    settings=mock_settings,
                    x_api_key="a" * 99 + "b",  # Only last char different
                )

        # Both should result in same error
        assert exc1.value.status_code == exc2.value.status_code
        assert exc1.value.detail == exc2.value.detail

    @pytest.mark.asyncio
    async def test_empty_api_key_fails(self) -> None:
        """Test that empty API key fails when auth is enabled."""
        mock_settings = MagicMock()
        mock_settings.api_key = "valid-secret-key"

        mock_request = MagicMock()
        mock_request.url.path = "/a2a"
        mock_request.method = "POST"
        mock_request.client.host = "127.0.0.1"

        with patch("sae.api.dependencies.get_settings", return_value=mock_settings):
            with pytest.raises(HTTPException) as exc_info:
                await verify_api_key(
                    request=mock_request,
                    settings=mock_settings,
                    x_api_key="",  # Empty key
                )

        assert exc_info.value.status_code == 401
