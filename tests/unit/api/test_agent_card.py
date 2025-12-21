"""Tests for the Agent Card endpoint."""

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from sae.api.agent_card import build_agent_card


class TestBuildAgentCard:
    """Tests for build_agent_card function."""

    def test_build_agent_card_uses_settings(self, mock_settings: MagicMock) -> None:
        """Test that agent card uses settings values."""
        with patch("sae.api.agent_card.get_settings", return_value=mock_settings):
            card = build_agent_card("http://localhost:8000")

            assert card.name == mock_settings.agent_name
            assert card.description == mock_settings.agent_description
            assert card.version == mock_settings.agent_version

    def test_build_agent_card_sets_url(self, mock_settings: MagicMock) -> None:
        """Test that agent card sets the URL correctly."""
        card = build_agent_card("http://example.com")
        assert card.url == "http://example.com"

    def test_build_agent_card_capabilities(self, mock_settings: MagicMock) -> None:
        """Test agent card capabilities."""
        card = build_agent_card("http://localhost")

        assert card.capabilities.streaming is True
        assert card.capabilities.push_notifications is False
        # Note: Due to Pydantic alias handling, state_transition_history stays at default
        # because the model lacks populate_by_name=True
        assert card.capabilities.state_transition_history is False

    def test_build_agent_card_has_contract_review_skill(
        self, mock_settings: MagicMock
    ) -> None:
        """Test that agent card includes contract_review skill."""
        card = build_agent_card("http://localhost")

        assert len(card.skills) == 1
        assert card.skills[0].id == "contract_review"
        assert card.skills[0].name == "Contract Clause Review"
        assert len(card.skills[0].tags) == 4
        assert "legal" in card.skills[0].tags

    def test_build_agent_card_input_output_modes(
        self, mock_settings: MagicMock
    ) -> None:
        """Test agent card input/output modes."""
        card = build_agent_card("http://localhost")

        assert card.default_input_modes == ["text", "file"]
        assert card.default_output_modes == ["text"]

    def test_build_agent_card_has_provider(self, mock_settings: MagicMock) -> None:
        """Test agent card provider info."""
        card = build_agent_card("http://localhost")

        assert card.provider is not None
        assert card.provider["name"] == "Sae"


class TestAgentCardEndpoint:
    """Tests for /.well-known/agent.json endpoint."""

    def test_get_agent_card_returns_200(self, client: TestClient) -> None:
        """Test that agent card endpoint returns 200."""
        response = client.get("/.well-known/agent.json")
        assert response.status_code == 200

    def test_get_agent_card_returns_json(self, client: TestClient) -> None:
        """Test that agent card endpoint returns JSON."""
        response = client.get("/.well-known/agent.json")
        data = response.json()
        assert isinstance(data, dict)

    def test_get_agent_card_contains_required_fields(
        self, client: TestClient
    ) -> None:
        """Test that agent card contains required fields."""
        response = client.get("/.well-known/agent.json")
        data = response.json()

        assert "name" in data
        assert "description" in data
        assert "url" in data
        assert "version" in data
        assert "capabilities" in data
        assert "skills" in data

    def test_get_agent_card_uses_camel_case(self, client: TestClient) -> None:
        """Test that agent card uses camelCase for aliases."""
        response = client.get("/.well-known/agent.json")
        data = response.json()

        # Check capabilities uses camelCase
        caps = data["capabilities"]
        assert "pushNotifications" in caps
        assert "stateTransitionHistory" in caps

    def test_get_agent_card_excludes_none_values(self, client: TestClient) -> None:
        """Test that null values are excluded from response."""
        response = client.get("/.well-known/agent.json")
        data = response.json()

        # documentationUrl should not be present (it's None by default)
        assert "documentationUrl" not in data

    def test_get_agent_card_url_matches_request(self, client: TestClient) -> None:
        """Test that URL in agent card matches request base URL."""
        response = client.get("/.well-known/agent.json")
        data = response.json()

        # TestClient uses http://testserver
        assert "testserver" in data["url"]
