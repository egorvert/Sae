"""Tests for the analyze_risks node."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from sae.agents.nodes.analyze_risks import analyze_risks, get_llm
from sae.agents.state import ContractReviewState
from sae.models.clauses import ClauseType, ExtractedClause, RiskLevel

from tests.fixtures.mock_llm_responses import (
    MOCK_RISK_ANALYSIS_JSON,
    MOCK_RISK_ANALYSIS_CRITICAL_JSON,
    MOCK_EMPTY_RISKS_JSON,
    MOCK_MALFORMED_JSON,
    MOCK_INVALID_RISK_LEVEL_JSON,
    MOCK_OUT_OF_RANGE_CONFIDENCE_JSON,
)


def create_sample_clauses() -> list[ExtractedClause]:
    """Create sample clauses for testing."""
    return [
        ExtractedClause(
            id="clause-001",
            type=ClauseType.CONFIDENTIALITY,
            title="Confidentiality",
            text="All information shall remain confidential.",
            location="Section 1",
        ),
        ExtractedClause(
            id="clause-002",
            type=ClauseType.LIABILITY,
            title="Liability",
            text="Total liability shall not exceed $1,000,000.",
            location="Section 3",
        ),
        ExtractedClause(
            id="clause-003",
            type=ClauseType.TERMINATION,
            title="Termination",
            text="Either party may terminate with 30 days notice.",
            location="Section 6",
        ),
    ]


def create_test_state(
    clauses: list[ExtractedClause] | None = None,
) -> ContractReviewState:
    """Create a test state for risk analysis."""
    return {
        "task_id": "test-task-001",
        "contract_text": "Sample contract text",
        "contract_metadata": {},
        "status": "analyzing",
        "error": None,
        "clauses": clauses or [],
        "risks": [],
        "recommendations": [],
        "messages": [],
    }


class TestGetLlm:
    """Tests for get_llm function."""

    def test_get_llm_uses_gpt4o(self, mock_settings: MagicMock) -> None:
        """Test that get_llm uses gpt-4o model."""
        with patch("sae.agents.nodes.analyze_risks.ChatOpenAI") as MockLLM:
            get_llm()
            MockLLM.assert_called_once()
            call_kwargs = MockLLM.call_args.kwargs
            assert call_kwargs["model"] == "gpt-4o"
            assert call_kwargs["temperature"] == 0


class TestAnalyzeRisks:
    """Tests for analyze_risks function."""

    async def test_analyze_risks_success(self, mock_settings: MagicMock) -> None:
        """Test successful risk analysis."""
        mock_response = MagicMock()
        mock_response.content = MOCK_RISK_ANALYSIS_JSON

        with patch("sae.agents.nodes.analyze_risks.ChatOpenAI") as MockLLM:
            mock_llm = AsyncMock()
            mock_llm.ainvoke = AsyncMock(return_value=mock_response)
            MockLLM.return_value = mock_llm

            state = create_test_state(create_sample_clauses())
            result = await analyze_risks(state)

            assert result["status"] == "recommending"
            assert len(result["risks"]) == 3
            # Check risk levels
            risk_levels = [r.risk_level for r in result["risks"]]
            assert RiskLevel.HIGH in risk_levels
            assert RiskLevel.LOW in risk_levels
            assert RiskLevel.MEDIUM in risk_levels

    async def test_analyze_risks_no_clauses_early_exit(
        self, mock_settings: MagicMock
    ) -> None:
        """Test early exit when no clauses to analyze."""
        state = create_test_state(clauses=[])
        result = await analyze_risks(state)

        assert result["status"] == "recommending"
        assert result["risks"] == []
        assert "No clauses found" in result["messages"][0].content

    async def test_analyze_risks_critical_detection(
        self, mock_settings: MagicMock
    ) -> None:
        """Test detection of critical risks."""
        mock_response = MagicMock()
        mock_response.content = MOCK_RISK_ANALYSIS_CRITICAL_JSON

        with patch("sae.agents.nodes.analyze_risks.ChatOpenAI") as MockLLM:
            mock_llm = AsyncMock()
            mock_llm.ainvoke = AsyncMock(return_value=mock_response)
            MockLLM.return_value = mock_llm

            state = create_test_state(create_sample_clauses())
            result = await analyze_risks(state)

            assert len(result["risks"]) == 1
            assert result["risks"][0].risk_level == RiskLevel.CRITICAL
            assert result["risks"][0].confidence == 0.95

    async def test_analyze_risks_confidence_clamped_high(
        self, mock_settings: MagicMock
    ) -> None:
        """Test that confidence > 1.0 is clamped to 1.0."""
        mock_response = MagicMock()
        mock_response.content = MOCK_OUT_OF_RANGE_CONFIDENCE_JSON

        with patch("sae.agents.nodes.analyze_risks.ChatOpenAI") as MockLLM:
            mock_llm = AsyncMock()
            mock_llm.ainvoke = AsyncMock(return_value=mock_response)
            MockLLM.return_value = mock_llm

            state = create_test_state(create_sample_clauses())
            result = await analyze_risks(state)

            # First risk has confidence 1.5, should be clamped to 1.0
            assert result["risks"][0].confidence == 1.0
            # Second risk has confidence -0.5, should be clamped to 0.0
            assert result["risks"][1].confidence == 0.0

    async def test_analyze_risks_invalid_level_defaults_to_low(
        self, mock_settings: MagicMock
    ) -> None:
        """Test that invalid risk levels default to LOW."""
        mock_response = MagicMock()
        mock_response.content = MOCK_INVALID_RISK_LEVEL_JSON

        with patch("sae.agents.nodes.analyze_risks.ChatOpenAI") as MockLLM:
            mock_llm = AsyncMock()
            mock_llm.ainvoke = AsyncMock(return_value=mock_response)
            MockLLM.return_value = mock_llm

            state = create_test_state(create_sample_clauses())
            result = await analyze_risks(state)

            # Unknown risk level should default to LOW
            assert result["risks"][0].risk_level == RiskLevel.LOW

    async def test_analyze_risks_parses_issues_array(
        self, mock_settings: MagicMock
    ) -> None:
        """Test that issues array is parsed correctly."""
        mock_response = MagicMock()
        mock_response.content = MOCK_RISK_ANALYSIS_CRITICAL_JSON

        with patch("sae.agents.nodes.analyze_risks.ChatOpenAI") as MockLLM:
            mock_llm = AsyncMock()
            mock_llm.ainvoke = AsyncMock(return_value=mock_response)
            MockLLM.return_value = mock_llm

            state = create_test_state(create_sample_clauses())
            result = await analyze_risks(state)

            assert len(result["risks"][0].issues) == 3
            assert "One-sided indemnification" in result["risks"][0].issues

    async def test_analyze_risks_json_decode_error(
        self, mock_settings: MagicMock
    ) -> None:
        """Test handling of JSON decode errors."""
        mock_response = MagicMock()
        mock_response.content = MOCK_MALFORMED_JSON

        with patch("sae.agents.nodes.analyze_risks.ChatOpenAI") as MockLLM:
            mock_llm = AsyncMock()
            mock_llm.ainvoke = AsyncMock(return_value=mock_response)
            MockLLM.return_value = mock_llm

            state = create_test_state(create_sample_clauses())
            result = await analyze_risks(state)

            assert result["status"] == "failed"
            assert "Failed to parse risk analysis" in result["error"]

    async def test_analyze_risks_llm_exception(self, mock_settings: MagicMock) -> None:
        """Test handling of LLM exceptions."""
        with patch("sae.agents.nodes.analyze_risks.ChatOpenAI") as MockLLM:
            mock_llm = AsyncMock()
            mock_llm.ainvoke = AsyncMock(side_effect=Exception("API Error"))
            MockLLM.return_value = mock_llm

            state = create_test_state(create_sample_clauses())
            result = await analyze_risks(state)

            assert result["status"] == "failed"
            assert "Risk analysis error" in result["error"]

    async def test_analyze_risks_adds_message_with_counts(
        self, mock_settings: MagicMock
    ) -> None:
        """Test that analysis adds a message with risk counts."""
        mock_response = MagicMock()
        mock_response.content = MOCK_RISK_ANALYSIS_JSON

        with patch("sae.agents.nodes.analyze_risks.ChatOpenAI") as MockLLM:
            mock_llm = AsyncMock()
            mock_llm.ainvoke = AsyncMock(return_value=mock_response)
            MockLLM.return_value = mock_llm

            state = create_test_state(create_sample_clauses())
            result = await analyze_risks(state)

            assert len(result["messages"]) == 1
            message = result["messages"][0].content
            assert "Analyzed" in message
            assert "critical" in message.lower() or "high" in message.lower()

    async def test_analyze_risks_empty_response(self, mock_settings: MagicMock) -> None:
        """Test handling of empty risks array."""
        mock_response = MagicMock()
        mock_response.content = MOCK_EMPTY_RISKS_JSON

        with patch("sae.agents.nodes.analyze_risks.ChatOpenAI") as MockLLM:
            mock_llm = AsyncMock()
            mock_llm.ainvoke = AsyncMock(return_value=mock_response)
            MockLLM.return_value = mock_llm

            state = create_test_state(create_sample_clauses())
            result = await analyze_risks(state)

            assert result["status"] == "recommending"
            assert result["risks"] == []
