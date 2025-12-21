"""Tests for the extract_clauses node."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from sae.agents.nodes.extract_clauses import extract_clauses, get_llm
from sae.agents.state import ContractReviewState
from sae.models.clauses import ClauseType

from tests.fixtures.mock_llm_responses import (
    MOCK_CLAUSE_EXTRACTION_JSON,
    MOCK_CLAUSE_EXTRACTION_PLAIN_JSON,
    MOCK_EMPTY_CLAUSES_JSON,
    MOCK_MALFORMED_JSON,
    MOCK_MISSING_FIELDS_JSON,
    MOCK_NESTED_MARKDOWN_JSON,
    MOCK_UNKNOWN_CLAUSE_TYPE_JSON,
)
from tests.fixtures.sample_contracts import SIMPLE_NDA


def create_test_state(contract_text: str = SIMPLE_NDA) -> ContractReviewState:
    """Create a test state for clause extraction."""
    return {
        "task_id": "test-task-001",
        "contract_text": contract_text,
        "contract_metadata": {},
        "status": "extracting",
        "error": None,
        "clauses": [],
        "risks": [],
        "recommendations": [],
        "messages": [],
    }


class TestGetLlm:
    """Tests for get_llm function."""

    def test_get_llm_uses_gpt4o(self, mock_settings: MagicMock) -> None:
        """Test that get_llm uses gpt-4o model."""
        with patch("sae.agents.nodes.extract_clauses.ChatOpenAI") as MockLLM:
            get_llm()
            MockLLM.assert_called_once()
            call_kwargs = MockLLM.call_args.kwargs
            assert call_kwargs["model"] == "gpt-4o"
            assert call_kwargs["temperature"] == 0

    def test_get_llm_uses_api_key_from_settings(self, mock_settings: MagicMock) -> None:
        """Test that get_llm uses API key from settings."""
        with patch("sae.agents.nodes.extract_clauses.get_settings", return_value=mock_settings):
            with patch("sae.agents.nodes.extract_clauses.ChatOpenAI") as MockLLM:
                get_llm()
                call_kwargs = MockLLM.call_args.kwargs
                assert call_kwargs["api_key"] == mock_settings.openai_api_key


class TestExtractClauses:
    """Tests for extract_clauses function."""

    async def test_extract_clauses_success(self, mock_settings: MagicMock) -> None:
        """Test successful clause extraction."""
        mock_response = MagicMock()
        mock_response.content = MOCK_CLAUSE_EXTRACTION_JSON

        with patch("sae.agents.nodes.extract_clauses.ChatOpenAI") as MockLLM:
            mock_llm = AsyncMock()
            mock_llm.ainvoke = AsyncMock(return_value=mock_response)
            MockLLM.return_value = mock_llm

            state = create_test_state()
            result = await extract_clauses(state)

            assert result["status"] == "analyzing"
            assert len(result["clauses"]) == 3
            assert result["clauses"][0].type == ClauseType.CONFIDENTIALITY
            assert result["clauses"][1].type == ClauseType.LIABILITY
            assert result["clauses"][2].type == ClauseType.TERMINATION

    async def test_extract_clauses_parses_plain_json(
        self, mock_settings: MagicMock
    ) -> None:
        """Test parsing plain JSON without markdown blocks."""
        mock_response = MagicMock()
        mock_response.content = MOCK_CLAUSE_EXTRACTION_PLAIN_JSON

        with patch("sae.agents.nodes.extract_clauses.ChatOpenAI") as MockLLM:
            mock_llm = AsyncMock()
            mock_llm.ainvoke = AsyncMock(return_value=mock_response)
            MockLLM.return_value = mock_llm

            state = create_test_state()
            result = await extract_clauses(state)

            assert result["status"] == "analyzing"
            assert len(result["clauses"]) == 1

    async def test_extract_clauses_handles_markdown_json(
        self, mock_settings: MagicMock
    ) -> None:
        """Test handling JSON wrapped in markdown code blocks."""
        mock_response = MagicMock()
        mock_response.content = MOCK_NESTED_MARKDOWN_JSON

        with patch("sae.agents.nodes.extract_clauses.ChatOpenAI") as MockLLM:
            mock_llm = AsyncMock()
            mock_llm.ainvoke = AsyncMock(return_value=mock_response)
            MockLLM.return_value = mock_llm

            state = create_test_state()
            result = await extract_clauses(state)

            assert result["status"] == "analyzing"
            assert len(result["clauses"]) == 1
            assert result["clauses"][0].type == ClauseType.WARRANTY

    async def test_extract_clauses_unknown_type_defaults_to_other(
        self, mock_settings: MagicMock
    ) -> None:
        """Test that unknown clause types default to OTHER."""
        mock_response = MagicMock()
        mock_response.content = MOCK_UNKNOWN_CLAUSE_TYPE_JSON

        with patch("sae.agents.nodes.extract_clauses.ChatOpenAI") as MockLLM:
            mock_llm = AsyncMock()
            mock_llm.ainvoke = AsyncMock(return_value=mock_response)
            MockLLM.return_value = mock_llm

            state = create_test_state()
            result = await extract_clauses(state)

            assert result["status"] == "analyzing"
            assert result["clauses"][0].type == ClauseType.OTHER

    async def test_extract_clauses_generates_ids(self, mock_settings: MagicMock) -> None:
        """Test that clause IDs are generated."""
        mock_response = MagicMock()
        mock_response.content = MOCK_CLAUSE_EXTRACTION_PLAIN_JSON

        with patch("sae.agents.nodes.extract_clauses.ChatOpenAI") as MockLLM:
            mock_llm = AsyncMock()
            mock_llm.ainvoke = AsyncMock(return_value=mock_response)
            MockLLM.return_value = mock_llm

            state = create_test_state()
            result = await extract_clauses(state)

            # IDs should be 8 characters (UUID prefix)
            assert len(result["clauses"][0].id) == 8

    async def test_extract_clauses_json_decode_error(
        self, mock_settings: MagicMock
    ) -> None:
        """Test handling of JSON decode errors."""
        mock_response = MagicMock()
        mock_response.content = MOCK_MALFORMED_JSON

        with patch("sae.agents.nodes.extract_clauses.ChatOpenAI") as MockLLM:
            mock_llm = AsyncMock()
            mock_llm.ainvoke = AsyncMock(return_value=mock_response)
            MockLLM.return_value = mock_llm

            state = create_test_state()
            result = await extract_clauses(state)

            assert result["status"] == "failed"
            assert "Failed to parse extracted clauses" in result["error"]

    async def test_extract_clauses_llm_exception(self, mock_settings: MagicMock) -> None:
        """Test handling of LLM exceptions."""
        with patch("sae.agents.nodes.extract_clauses.ChatOpenAI") as MockLLM:
            mock_llm = AsyncMock()
            mock_llm.ainvoke = AsyncMock(side_effect=Exception("API Error"))
            MockLLM.return_value = mock_llm

            state = create_test_state()
            result = await extract_clauses(state)

            assert result["status"] == "failed"
            assert "Clause extraction error" in result["error"]

    async def test_extract_clauses_empty_response(
        self, mock_settings: MagicMock
    ) -> None:
        """Test handling of empty clause array."""
        mock_response = MagicMock()
        mock_response.content = MOCK_EMPTY_CLAUSES_JSON

        with patch("sae.agents.nodes.extract_clauses.ChatOpenAI") as MockLLM:
            mock_llm = AsyncMock()
            mock_llm.ainvoke = AsyncMock(return_value=mock_response)
            MockLLM.return_value = mock_llm

            state = create_test_state()
            result = await extract_clauses(state)

            assert result["status"] == "analyzing"
            assert result["clauses"] == []

    async def test_extract_clauses_missing_fields_uses_defaults(
        self, mock_settings: MagicMock
    ) -> None:
        """Test that missing fields use default values."""
        mock_response = MagicMock()
        mock_response.content = MOCK_MISSING_FIELDS_JSON

        with patch("sae.agents.nodes.extract_clauses.ChatOpenAI") as MockLLM:
            mock_llm = AsyncMock()
            mock_llm.ainvoke = AsyncMock(return_value=mock_response)
            MockLLM.return_value = mock_llm

            state = create_test_state()
            result = await extract_clauses(state)

            assert result["status"] == "analyzing"
            clause = result["clauses"][0]
            assert clause.title == "Clause 1"  # Default title
            assert clause.text == ""  # Default text
            assert clause.location == "Section 1"  # Default location

    async def test_extract_clauses_adds_message(self, mock_settings: MagicMock) -> None:
        """Test that extraction adds a message to the state."""
        mock_response = MagicMock()
        mock_response.content = MOCK_CLAUSE_EXTRACTION_JSON

        with patch("sae.agents.nodes.extract_clauses.ChatOpenAI") as MockLLM:
            mock_llm = AsyncMock()
            mock_llm.ainvoke = AsyncMock(return_value=mock_response)
            MockLLM.return_value = mock_llm

            state = create_test_state()
            result = await extract_clauses(state)

            assert len(result["messages"]) == 1
            assert "Extracted 3 clauses" in result["messages"][0].content
