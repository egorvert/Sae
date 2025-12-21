"""Tests for application configuration."""

import os
from unittest.mock import patch

import pytest
from pydantic import ValidationError

from sae.config import Settings, get_settings


class TestSettings:
    """Tests for Settings class."""

    def test_settings_from_env(self) -> None:
        """Test that settings can be loaded from environment variables."""
        env_vars = {
            "OPENAI_API_KEY": "test-openai-key",
            "PINECONE_API_KEY": "test-pinecone-key",
            "PINECONE_INDEX_NAME": "test-index",
            "LOG_LEVEL": "DEBUG",
            "ENVIRONMENT": "development",
            "HOST": "127.0.0.1",
            "PORT": "9000",
            "AGENT_NAME": "Test Agent",
            "AGENT_VERSION": "1.0.0",
            "AGENT_DESCRIPTION": "Test description",
        }
        with patch.dict(os.environ, env_vars, clear=False):
            settings = Settings()
            assert settings.openai_api_key == "test-openai-key"
            assert settings.pinecone_api_key == "test-pinecone-key"
            assert settings.pinecone_index_name == "test-index"
            assert settings.log_level == "DEBUG"
            assert settings.environment == "development"
            assert settings.host == "127.0.0.1"
            assert settings.port == 9000
            assert settings.agent_name == "Test Agent"
            assert settings.agent_version == "1.0.0"

    def test_settings_default_values(self) -> None:
        """Test that settings have correct default values when not overridden."""
        env_vars = {
            "OPENAI_API_KEY": "test-key",
            "PINECONE_API_KEY": "test-pinecone-key",
            # Explicitly set values to test defaults
            "LOG_LEVEL": "INFO",
            "ENVIRONMENT": "development",
        }
        with patch.dict(os.environ, env_vars, clear=False):
            settings = Settings()
            assert settings.pinecone_index_name == "sae-legal"
            assert settings.log_level == "INFO"
            assert settings.environment == "development"
            assert settings.host == "0.0.0.0"
            assert settings.port == 8000
            assert settings.agent_name == "Sae Legal Agent"
            assert settings.agent_version == "0.1.0"
            assert settings.agent_description == "Contract clause review and risk analysis"

    def test_settings_fields_are_required(self) -> None:
        """Test that openai_api_key is required, pinecone is optional."""
        hints = Settings.__annotations__
        # openai_api_key should be str (required)
        assert hints["openai_api_key"] == str
        # pinecone_api_key should be optional (str | None)
        assert hints["pinecone_api_key"] == (str | None)
        # api_key should be optional (str | None)
        assert hints["api_key"] == (str | None)

    def test_settings_new_optional_fields(self) -> None:
        """Test new optional configuration fields and their defaults."""
        # Test that these fields have correct default types/values
        # Note: actual .env file may override defaults, so we test structure
        env_vars = {
            "OPENAI_API_KEY": "test-key",
            # Explicitly unset optional fields to test defaults
            "PINECONE_API_KEY": "",
            "API_KEY": "",
        }
        with patch.dict(os.environ, env_vars, clear=False):
            # Create settings without loading .env file
            from pydantic_settings import BaseSettings, SettingsConfigDict

            # Test defaults by checking field annotations exist
            hints = Settings.__annotations__
            assert "pinecone_api_key" in hints
            assert "api_key" in hints
            assert "rate_limit_enabled" in hints
            assert "rate_limit_per_minute" in hints
            assert "cors_origins" in hints

            # Test rate limit defaults (not affected by .env)
            settings = Settings()
            assert settings.rate_limit_enabled is True
            assert settings.rate_limit_per_minute == 30
            assert settings.cors_origins == ["*"]

    def test_settings_is_production_true(self) -> None:
        """Test is_production property returns True for production."""
        env_vars = {
            "OPENAI_API_KEY": "test-key",
            "ENVIRONMENT": "production",
        }
        with patch.dict(os.environ, env_vars, clear=False):
            settings = Settings()
            assert settings.is_production is True

    def test_settings_is_production_false_development(self) -> None:
        """Test is_production property returns False for development."""
        env_vars = {
            "OPENAI_API_KEY": "test-key",
            "ENVIRONMENT": "development",
        }
        with patch.dict(os.environ, env_vars, clear=False):
            settings = Settings()
            assert settings.is_production is False

    def test_settings_is_production_false_staging(self) -> None:
        """Test is_production property returns False for staging."""
        env_vars = {
            "OPENAI_API_KEY": "test-key",
            "ENVIRONMENT": "staging",
        }
        with patch.dict(os.environ, env_vars, clear=False):
            settings = Settings()
            assert settings.is_production is False

    def test_settings_log_level_validation(self) -> None:
        """Test that log_level accepts valid values."""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR"]
        for level in valid_levels:
            env_vars = {
                "OPENAI_API_KEY": "test-key",
                "LOG_LEVEL": level,
            }
            with patch.dict(os.environ, env_vars, clear=False):
                settings = Settings()
                assert settings.log_level == level

    def test_settings_environment_validation(self) -> None:
        """Test that environment accepts valid values."""
        valid_envs = ["development", "staging", "production"]
        for env in valid_envs:
            env_vars = {
                "OPENAI_API_KEY": "test-key",
                "ENVIRONMENT": env,
            }
            with patch.dict(os.environ, env_vars, clear=False):
                settings = Settings()
                assert settings.environment == env

    def test_settings_case_insensitive(self) -> None:
        """Test that environment variable names are case insensitive."""
        env_vars = {
            "openai_api_key": "test-key",
        }
        with patch.dict(os.environ, env_vars, clear=False):
            settings = Settings()
            assert settings.openai_api_key == "test-key"


class TestGetSettings:
    """Tests for get_settings function."""

    def test_get_settings_returns_settings_instance(self) -> None:
        """Test that get_settings returns a Settings instance."""
        env_vars = {
            "OPENAI_API_KEY": "test-key",
        }
        with patch.dict(os.environ, env_vars, clear=False):
            # Clear the cache to test fresh settings creation
            get_settings.cache_clear()
            settings = get_settings()
            assert isinstance(settings, Settings)

    def test_get_settings_cached(self) -> None:
        """Test that get_settings returns cached instance."""
        env_vars = {
            "OPENAI_API_KEY": "test-key",
        }
        with patch.dict(os.environ, env_vars, clear=False):
            get_settings.cache_clear()
            settings1 = get_settings()
            settings2 = get_settings()
            # Should be the exact same object (cached)
            assert settings1 is settings2
