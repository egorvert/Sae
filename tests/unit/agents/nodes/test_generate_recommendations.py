"""Tests for the generate_recommendations node."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from sae.agents.nodes.generate_recommendations import generate_recommendations, get_llm
from sae.agents.state import ContractReviewState
from sae.models.clauses import ClauseType, ExtractedClause, RiskAssessment, RiskLevel

from tests.fixtures.mock_llm_responses import (
    MOCK_RECOMMENDATIONS_JSON,
    MOCK_EMPTY_RECOMMENDATIONS_JSON,
    MOCK_MALFORMED_JSON,
    MOCK_OUT_OF_RANGE_PRIORITY_JSON,
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


def create_sample_risks() -> list[RiskAssessment]:
    """Create sample risk assessments for testing."""
    return [
        RiskAssessment(
            clause_id="clause-001",
            risk_level=RiskLevel.LOW,
            confidence=0.92,
            issues=[],
            explanation="Standard confidentiality clause.",
            affected_party="both",
        ),
        RiskAssessment(
            clause_id="clause-002",
            risk_level=RiskLevel.HIGH,
            confidence=0.85,
            issues=["Low liability cap"],
            explanation="Liability cap may be insufficient.",
            affected_party="client",
        ),
        RiskAssessment(
            clause_id="clause-003",
            risk_level=RiskLevel.MEDIUM,
            confidence=0.78,
            issues=["Short notice period"],
            explanation="30 days may not be enough.",
            affected_party="client",
        ),
    ]


def create_test_state(
    clauses: list[ExtractedClause] | None = None,
    risks: list[RiskAssessment] | None = None,
) -> ContractReviewState:
    """Create a test state for recommendation generation."""
    return {
        "task_id": "test-task-001",
        "contract_text": "Sample contract text",
        "contract_metadata": {},
        "status": "recommending",
        "error": None,
        "clauses": clauses or [],
        "risks": risks or [],
        "recommendations": [],
        "messages": [],
    }


class TestGetLlm:
    """Tests for get_llm function."""

    def test_get_llm_uses_gpt4o(self, mock_settings: MagicMock) -> None:
        """Test that get_llm uses gpt-4o model."""
        with patch("sae.agents.nodes.generate_recommendations.ChatOpenAI") as MockLLM:
            get_llm()
            MockLLM.assert_called_once()
            call_kwargs = MockLLM.call_args.kwargs
            assert call_kwargs["model"] == "gpt-4o"

    def test_get_llm_uses_temperature_0_1(self, mock_settings: MagicMock) -> None:
        """Test that get_llm uses temperature 0.1 for creativity."""
        with patch("sae.agents.nodes.generate_recommendations.ChatOpenAI") as MockLLM:
            get_llm()
            call_kwargs = MockLLM.call_args.kwargs
            assert call_kwargs["temperature"] == 0.1


class TestGenerateRecommendations:
    """Tests for generate_recommendations function."""

    async def test_generate_recommendations_success(
        self, mock_settings: MagicMock
    ) -> None:
        """Test successful recommendation generation."""
        mock_response = MagicMock()
        mock_response.content = MOCK_RECOMMENDATIONS_JSON

        with patch("sae.agents.nodes.generate_recommendations.ChatOpenAI") as MockLLM:
            mock_llm = AsyncMock()
            mock_llm.ainvoke = AsyncMock(return_value=mock_response)
            MockLLM.return_value = mock_llm

            state = create_test_state(
                clauses=create_sample_clauses(),
                risks=create_sample_risks(),
            )
            result = await generate_recommendations(state)

            assert result["status"] == "complete"
            assert len(result["recommendations"]) == 3

    async def test_generate_recommendations_no_risks_early_exit(
        self, mock_settings: MagicMock
    ) -> None:
        """Test early exit when no risks to address."""
        state = create_test_state(clauses=create_sample_clauses(), risks=[])
        result = await generate_recommendations(state)

        assert result["status"] == "complete"
        assert result["recommendations"] == []
        assert "No significant risks found" in result["messages"][0].content

    async def test_generate_recommendations_sorted_by_priority(
        self, mock_settings: MagicMock
    ) -> None:
        """Test that recommendations are sorted by priority."""
        mock_response = MagicMock()
        mock_response.content = MOCK_RECOMMENDATIONS_JSON

        with patch("sae.agents.nodes.generate_recommendations.ChatOpenAI") as MockLLM:
            mock_llm = AsyncMock()
            mock_llm.ainvoke = AsyncMock(return_value=mock_response)
            MockLLM.return_value = mock_llm

            state = create_test_state(
                clauses=create_sample_clauses(),
                risks=create_sample_risks(),
            )
            result = await generate_recommendations(state)

            priorities = [r.priority for r in result["recommendations"]]
            assert priorities == sorted(priorities)

    async def test_generate_recommendations_priority_clamped_low(
        self, mock_settings: MagicMock
    ) -> None:
        """Test that priority < 1 is clamped to 1."""
        mock_response = MagicMock()
        mock_response.content = MOCK_OUT_OF_RANGE_PRIORITY_JSON

        with patch("sae.agents.nodes.generate_recommendations.ChatOpenAI") as MockLLM:
            mock_llm = AsyncMock()
            mock_llm.ainvoke = AsyncMock(return_value=mock_response)
            MockLLM.return_value = mock_llm

            state = create_test_state(
                clauses=create_sample_clauses(),
                risks=create_sample_risks(),
            )
            result = await generate_recommendations(state)

            # First recommendation has priority 0, should be clamped to 1
            assert result["recommendations"][0].priority == 1

    async def test_generate_recommendations_priority_clamped_high(
        self, mock_settings: MagicMock
    ) -> None:
        """Test that priority > 5 is clamped to 5."""
        mock_response = MagicMock()
        mock_response.content = MOCK_OUT_OF_RANGE_PRIORITY_JSON

        with patch("sae.agents.nodes.generate_recommendations.ChatOpenAI") as MockLLM:
            mock_llm = AsyncMock()
            mock_llm.ainvoke = AsyncMock(return_value=mock_response)
            MockLLM.return_value = mock_llm

            state = create_test_state(
                clauses=create_sample_clauses(),
                risks=create_sample_risks(),
            )
            result = await generate_recommendations(state)

            # Second recommendation has priority 10, should be clamped to 5
            assert result["recommendations"][1].priority == 5

    async def test_generate_recommendations_parses_risk_reduction(
        self, mock_settings: MagicMock
    ) -> None:
        """Test that risk_reduction RiskLevel is parsed correctly."""
        mock_response = MagicMock()
        mock_response.content = MOCK_RECOMMENDATIONS_JSON

        with patch("sae.agents.nodes.generate_recommendations.ChatOpenAI") as MockLLM:
            mock_llm = AsyncMock()
            mock_llm.ainvoke = AsyncMock(return_value=mock_response)
            MockLLM.return_value = mock_llm

            state = create_test_state(
                clauses=create_sample_clauses(),
                risks=create_sample_risks(),
            )
            result = await generate_recommendations(state)

            # First recommendation should have risk_reduction=medium
            assert result["recommendations"][0].risk_reduction == RiskLevel.MEDIUM

    async def test_generate_recommendations_null_suggested_text(
        self, mock_settings: MagicMock
    ) -> None:
        """Test that null suggested_text is allowed."""
        mock_response = MagicMock()
        mock_response.content = MOCK_RECOMMENDATIONS_JSON

        with patch("sae.agents.nodes.generate_recommendations.ChatOpenAI") as MockLLM:
            mock_llm = AsyncMock()
            mock_llm.ainvoke = AsyncMock(return_value=mock_response)
            MockLLM.return_value = mock_llm

            state = create_test_state(
                clauses=create_sample_clauses(),
                risks=create_sample_risks(),
            )
            result = await generate_recommendations(state)

            # Third recommendation has null suggested_text
            assert result["recommendations"][2].suggested_text is None

    async def test_generate_recommendations_json_decode_error(
        self, mock_settings: MagicMock
    ) -> None:
        """Test handling of JSON decode errors."""
        mock_response = MagicMock()
        mock_response.content = MOCK_MALFORMED_JSON

        with patch("sae.agents.nodes.generate_recommendations.ChatOpenAI") as MockLLM:
            mock_llm = AsyncMock()
            mock_llm.ainvoke = AsyncMock(return_value=mock_response)
            MockLLM.return_value = mock_llm

            state = create_test_state(
                clauses=create_sample_clauses(),
                risks=create_sample_risks(),
            )
            result = await generate_recommendations(state)

            assert result["status"] == "failed"
            assert "Failed to parse recommendations" in result["error"]

    async def test_generate_recommendations_llm_exception(
        self, mock_settings: MagicMock
    ) -> None:
        """Test handling of LLM exceptions."""
        with patch("sae.agents.nodes.generate_recommendations.ChatOpenAI") as MockLLM:
            mock_llm = AsyncMock()
            mock_llm.ainvoke = AsyncMock(side_effect=Exception("API Error"))
            MockLLM.return_value = mock_llm

            state = create_test_state(
                clauses=create_sample_clauses(),
                risks=create_sample_risks(),
            )
            result = await generate_recommendations(state)

            assert result["status"] == "failed"
            assert "Recommendation error" in result["error"]

    async def test_generate_recommendations_adds_message(
        self, mock_settings: MagicMock
    ) -> None:
        """Test that recommendation generation adds a message."""
        mock_response = MagicMock()
        mock_response.content = MOCK_RECOMMENDATIONS_JSON

        with patch("sae.agents.nodes.generate_recommendations.ChatOpenAI") as MockLLM:
            mock_llm = AsyncMock()
            mock_llm.ainvoke = AsyncMock(return_value=mock_response)
            MockLLM.return_value = mock_llm

            state = create_test_state(
                clauses=create_sample_clauses(),
                risks=create_sample_risks(),
            )
            result = await generate_recommendations(state)

            assert len(result["messages"]) == 1
            message = result["messages"][0].content
            assert "Generated" in message
            assert "recommendations" in message.lower()

    async def test_generate_recommendations_uses_clause_map(
        self, mock_settings: MagicMock
    ) -> None:
        """Test that clause text is included in LLM context."""
        mock_response = MagicMock()
        mock_response.content = MOCK_RECOMMENDATIONS_JSON

        with patch("sae.agents.nodes.generate_recommendations.ChatOpenAI") as MockLLM:
            mock_llm = AsyncMock()
            mock_llm.ainvoke = AsyncMock(return_value=mock_response)
            MockLLM.return_value = mock_llm

            clauses = create_sample_clauses()
            risks = create_sample_risks()
            state = create_test_state(clauses=clauses, risks=risks)

            await generate_recommendations(state)

            # Verify the LLM was called with clause context
            call_args = mock_llm.ainvoke.call_args
            messages = call_args[0][0]
            human_message = messages[1].content

            # The message should contain clause titles
            assert "Confidentiality" in human_message or "Liability" in human_message
