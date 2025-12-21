"""Tests for the contract review workflow."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from sae.agents.contract_review import (
    create_contract_review_graph,
    run_contract_review,
    should_continue,
)
from sae.agents.state import ContractInput, ContractReviewState
from sae.models.clauses import ClauseType, ExtractedClause, RiskAssessment, RiskLevel


def create_test_state(
    status: str = "pending",
    clauses: list | None = None,
    risks: list | None = None,
    recommendations: list | None = None,
    error: str | None = None,
) -> ContractReviewState:
    """Create a test ContractReviewState."""
    return {
        "task_id": "test-task-001",
        "contract_text": "Sample contract",
        "contract_metadata": {},
        "status": status,  # type: ignore
        "error": error,
        "clauses": clauses or [],
        "risks": risks or [],
        "recommendations": recommendations or [],
        "messages": [],
    }


class TestShouldContinue:
    """Tests for should_continue router function."""

    def test_should_continue_failed_returns_end(self) -> None:
        """Test that failed status returns 'end'."""
        state = create_test_state(status="failed")
        result = should_continue(state)
        assert result == "end"

    def test_should_continue_extracting_returns_extract(self) -> None:
        """Test that extracting status returns 'extract'."""
        state = create_test_state(status="extracting")
        result = should_continue(state)
        assert result == "extract"

    def test_should_continue_analyzing_returns_analyze(self) -> None:
        """Test that analyzing status returns 'analyze'."""
        state = create_test_state(status="analyzing")
        result = should_continue(state)
        assert result == "analyze"

    def test_should_continue_recommending_returns_recommend(self) -> None:
        """Test that recommending status returns 'recommend'."""
        state = create_test_state(status="recommending")
        result = should_continue(state)
        assert result == "recommend"

    def test_should_continue_complete_returns_end(self) -> None:
        """Test that complete status returns 'end'."""
        state = create_test_state(status="complete")
        result = should_continue(state)
        assert result == "end"

    def test_should_continue_pending_returns_extract(self) -> None:
        """Test that pending (default) status returns 'extract'."""
        state = create_test_state(status="pending")
        result = should_continue(state)
        assert result == "extract"

    def test_should_continue_unknown_returns_extract(self) -> None:
        """Test that unknown status returns 'extract' as default."""
        state = create_test_state()
        state["status"] = "unknown"  # type: ignore
        result = should_continue(state)
        assert result == "extract"


class TestCreateContractReviewGraph:
    """Tests for create_contract_review_graph function."""

    def test_creates_compiled_graph(self) -> None:
        """Test that create_contract_review_graph returns a compiled graph."""
        graph = create_contract_review_graph()
        # CompiledGraph should have ainvoke method
        assert hasattr(graph, "ainvoke")


class TestRunContractReview:
    """Tests for run_contract_review function."""

    async def test_run_contract_review_success(self, mock_settings: MagicMock) -> None:
        """Test successful contract review run."""
        # Create sample output data
        sample_clauses = [
            ExtractedClause(
                id="c1",
                type=ClauseType.LIABILITY,
                title="Liability",
                text="Test",
                location="Section 1",
            )
        ]
        sample_risks = [
            RiskAssessment(
                clause_id="c1",
                risk_level=RiskLevel.HIGH,
                confidence=0.85,
                explanation="Test risk",
            )
        ]

        mock_final_state = {
            "status": "complete",
            "clauses": sample_clauses,
            "risks": sample_risks,
            "recommendations": [],
            "error": None,
        }

        with patch("sae.agents.contract_review.contract_review_graph") as mock_graph:
            mock_graph.ainvoke = AsyncMock(return_value=mock_final_state)

            input_data = ContractInput(
                task_id="test-001",
                contract_text="Sample contract text",
            )
            result = await run_contract_review(input_data)

            assert result.success is True
            assert result.task_id == "test-001"
            assert result.error is None
            assert len(result.analysis.clauses) == 1
            assert len(result.analysis.risks) == 1

    async def test_run_contract_review_failed_state(
        self, mock_settings: MagicMock
    ) -> None:
        """Test contract review with failed state."""
        mock_final_state = {
            "status": "failed",
            "clauses": [],
            "risks": [],
            "recommendations": [],
            "error": "Failed to parse JSON",
        }

        with patch("sae.agents.contract_review.contract_review_graph") as mock_graph:
            mock_graph.ainvoke = AsyncMock(return_value=mock_final_state)

            input_data = ContractInput(
                task_id="test-002",
                contract_text="Sample contract text",
            )
            result = await run_contract_review(input_data)

            assert result.success is False
            assert result.error == "Failed to parse JSON"
            assert result.analysis.overall_risk == RiskLevel.HIGH

    async def test_run_contract_review_exception_handled(
        self, mock_settings: MagicMock
    ) -> None:
        """Test that exceptions are caught and returned as error."""
        with patch("sae.agents.contract_review.contract_review_graph") as mock_graph:
            mock_graph.ainvoke = AsyncMock(side_effect=Exception("Graph execution error"))

            input_data = ContractInput(
                task_id="test-003",
                contract_text="Sample contract text",
            )
            result = await run_contract_review(input_data)

            assert result.success is False
            assert "Graph execution error" in result.error  # type: ignore
            assert result.analysis.overall_risk == RiskLevel.HIGH

    async def test_overall_risk_critical_if_any_critical(
        self, mock_settings: MagicMock
    ) -> None:
        """Test that overall risk is CRITICAL if any risk is critical."""
        sample_risks = [
            RiskAssessment(
                clause_id="c1",
                risk_level=RiskLevel.LOW,
                confidence=0.9,
                explanation="Low risk",
            ),
            RiskAssessment(
                clause_id="c2",
                risk_level=RiskLevel.CRITICAL,
                confidence=0.95,
                explanation="Critical risk",
            ),
        ]

        mock_final_state = {
            "status": "complete",
            "clauses": [],
            "risks": sample_risks,
            "recommendations": [],
            "error": None,
        }

        with patch("sae.agents.contract_review.contract_review_graph") as mock_graph:
            mock_graph.ainvoke = AsyncMock(return_value=mock_final_state)

            input_data = ContractInput(
                task_id="test-004",
                contract_text="Sample contract text",
            )
            result = await run_contract_review(input_data)

            assert result.analysis.overall_risk == RiskLevel.CRITICAL

    async def test_overall_risk_high_if_any_high(
        self, mock_settings: MagicMock
    ) -> None:
        """Test that overall risk is HIGH if any risk is high (no critical)."""
        sample_risks = [
            RiskAssessment(
                clause_id="c1",
                risk_level=RiskLevel.LOW,
                confidence=0.9,
                explanation="Low risk",
            ),
            RiskAssessment(
                clause_id="c2",
                risk_level=RiskLevel.HIGH,
                confidence=0.85,
                explanation="High risk",
            ),
        ]

        mock_final_state = {
            "status": "complete",
            "clauses": [],
            "risks": sample_risks,
            "recommendations": [],
            "error": None,
        }

        with patch("sae.agents.contract_review.contract_review_graph") as mock_graph:
            mock_graph.ainvoke = AsyncMock(return_value=mock_final_state)

            input_data = ContractInput(
                task_id="test-005",
                contract_text="Sample contract text",
            )
            result = await run_contract_review(input_data)

            assert result.analysis.overall_risk == RiskLevel.HIGH

    async def test_overall_risk_medium_if_any_medium(
        self, mock_settings: MagicMock
    ) -> None:
        """Test that overall risk is MEDIUM if highest risk is medium."""
        sample_risks = [
            RiskAssessment(
                clause_id="c1",
                risk_level=RiskLevel.LOW,
                confidence=0.9,
                explanation="Low risk",
            ),
            RiskAssessment(
                clause_id="c2",
                risk_level=RiskLevel.MEDIUM,
                confidence=0.8,
                explanation="Medium risk",
            ),
        ]

        mock_final_state = {
            "status": "complete",
            "clauses": [],
            "risks": sample_risks,
            "recommendations": [],
            "error": None,
        }

        with patch("sae.agents.contract_review.contract_review_graph") as mock_graph:
            mock_graph.ainvoke = AsyncMock(return_value=mock_final_state)

            input_data = ContractInput(
                task_id="test-006",
                contract_text="Sample contract text",
            )
            result = await run_contract_review(input_data)

            assert result.analysis.overall_risk == RiskLevel.MEDIUM

    async def test_overall_risk_low_if_all_low(
        self, mock_settings: MagicMock
    ) -> None:
        """Test that overall risk is LOW if all risks are low."""
        sample_risks = [
            RiskAssessment(
                clause_id="c1",
                risk_level=RiskLevel.LOW,
                confidence=0.9,
                explanation="Low risk",
            ),
            RiskAssessment(
                clause_id="c2",
                risk_level=RiskLevel.LOW,
                confidence=0.88,
                explanation="Also low risk",
            ),
        ]

        mock_final_state = {
            "status": "complete",
            "clauses": [],
            "risks": sample_risks,
            "recommendations": [],
            "error": None,
        }

        with patch("sae.agents.contract_review.contract_review_graph") as mock_graph:
            mock_graph.ainvoke = AsyncMock(return_value=mock_final_state)

            input_data = ContractInput(
                task_id="test-007",
                contract_text="Sample contract text",
            )
            result = await run_contract_review(input_data)

            assert result.analysis.overall_risk == RiskLevel.LOW

    async def test_summary_includes_counts(self, mock_settings: MagicMock) -> None:
        """Test that the summary includes clause, risk, and recommendation counts."""
        sample_clauses = [
            ExtractedClause(
                id=f"c{i}",
                type=ClauseType.OTHER,
                title=f"Clause {i}",
                text="Test",
                location=f"Section {i}",
            )
            for i in range(5)
        ]
        sample_risks = [
            RiskAssessment(
                clause_id=f"c{i}",
                risk_level=RiskLevel.MEDIUM,
                confidence=0.8,
                explanation="Test",
            )
            for i in range(3)
        ]

        mock_final_state = {
            "status": "complete",
            "clauses": sample_clauses,
            "risks": sample_risks,
            "recommendations": [],
            "error": None,
        }

        with patch("sae.agents.contract_review.contract_review_graph") as mock_graph:
            mock_graph.ainvoke = AsyncMock(return_value=mock_final_state)

            input_data = ContractInput(
                task_id="test-008",
                contract_text="Sample contract text",
            )
            result = await run_contract_review(input_data)

            assert "5 clauses" in result.analysis.summary
            assert "3" in result.analysis.summary  # risk count

    async def test_input_metadata_passed_to_output(
        self, mock_settings: MagicMock
    ) -> None:
        """Test that input metadata is passed to output analysis."""
        mock_final_state = {
            "status": "complete",
            "clauses": [],
            "risks": [],
            "recommendations": [],
            "error": None,
        }

        with patch("sae.agents.contract_review.contract_review_graph") as mock_graph:
            mock_graph.ainvoke = AsyncMock(return_value=mock_final_state)

            input_data = ContractInput(
                task_id="test-009",
                contract_text="Sample contract text",
                metadata={"source": "test", "version": 1},
            )
            result = await run_contract_review(input_data)

            assert result.analysis.metadata["source"] == "test"
            assert result.analysis.metadata["version"] == 1


class TestContractInput:
    """Tests for ContractInput model."""

    def test_contract_input_creation(self) -> None:
        """Test creating a ContractInput."""
        input_data = ContractInput(
            task_id="test-001",
            contract_text="Contract text here",
        )
        assert input_data.task_id == "test-001"
        assert input_data.contract_text == "Contract text here"
        assert input_data.metadata == {}

    def test_contract_input_with_metadata(self) -> None:
        """Test ContractInput with metadata."""
        input_data = ContractInput(
            task_id="test-002",
            contract_text="Contract text",
            metadata={"source": "api"},
        )
        assert input_data.metadata["source"] == "api"
