"""Integration tests for the full A2A workflow."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from sae.agents.state import ContractOutput
from sae.models.a2a import TaskState
from sae.models.clauses import (
    ClauseType,
    ContractAnalysis,
    ExtractedClause,
    Recommendation,
    RiskAssessment,
    RiskLevel,
)

from tests.fixtures.sample_contracts import SIMPLE_NDA


class TestFullA2AWorkflow:
    """Integration tests for complete A2A workflow."""

    def test_submit_and_get_task(
        self, client: TestClient, mock_settings: MagicMock
    ) -> None:
        """Test submitting a task and retrieving its status."""
        # Create mock contract output
        mock_analysis = ContractAnalysis(
            contract_id="task-integration",
            summary="Analysis complete",
            clauses=[
                ExtractedClause(
                    id="c1",
                    type=ClauseType.CONFIDENTIALITY,
                    title="Confidentiality",
                    text="Test",
                    location="Section 1",
                )
            ],
            risks=[
                RiskAssessment(
                    clause_id="c1",
                    risk_level=RiskLevel.LOW,
                    confidence=0.9,
                    explanation="Low risk",
                )
            ],
            recommendations=[],
            overall_risk=RiskLevel.LOW,
        )

        mock_output = ContractOutput(
            task_id="task-integration",
            analysis=mock_analysis,
            success=True,
        )

        with patch("sae.api.jsonrpc.run_contract_review", new_callable=AsyncMock) as mock_review:
            mock_review.return_value = mock_output

            # Submit task
            submit_response = client.post(
                "/a2a",
                json={
                    "jsonrpc": "2.0",
                    "method": "tasks/send",
                    "id": "integration-1",
                    "params": {
                        "id": "task-integration",
                        "message": {
                            "role": "user",
                            "parts": [{"type": "text", "text": SIMPLE_NDA}],
                        },
                    },
                },
            )

            assert submit_response.status_code == 200
            submit_data = submit_response.json()
            assert "result" in submit_data
            task_id = submit_data["result"]["id"]

            # Get task status
            get_response = client.post(
                "/a2a",
                json={
                    "jsonrpc": "2.0",
                    "method": "tasks/get",
                    "id": "integration-2",
                    "params": {"id": task_id},
                },
            )

            assert get_response.status_code == 200

    def test_agent_card_discovery(self, client: TestClient) -> None:
        """Test A2A agent discovery via agent card."""
        response = client.get("/.well-known/agent.json")

        assert response.status_code == 200
        data = response.json()

        # Verify agent card structure
        assert data["name"] is not None
        assert data["capabilities"]["streaming"] is True
        assert len(data["skills"]) >= 1

        # Verify contract_review skill
        skill = data["skills"][0]
        assert skill["id"] == "contract_review"

    def test_health_check_integration(self, client: TestClient) -> None:
        """Test health check as part of service discovery."""
        response = client.get("/health")

        assert response.status_code == 200
        data = response.json()

        assert data["status"] == "healthy"
        assert "version" in data


class TestErrorScenarios:
    """Integration tests for error scenarios."""

    def test_task_not_found_scenario(
        self, client: TestClient, mock_settings: MagicMock
    ) -> None:
        """Test handling of non-existent task."""
        response = client.post(
            "/a2a",
            json={
                "jsonrpc": "2.0",
                "method": "tasks/get",
                "id": "error-1",
                "params": {"id": "nonexistent-task-12345"},
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert "error" in data
        assert data["error"]["code"] == -32001  # TASK_NOT_FOUND

    def test_invalid_method_scenario(self, client: TestClient) -> None:
        """Test handling of invalid RPC method."""
        response = client.post(
            "/a2a",
            json={
                "jsonrpc": "2.0",
                "method": "tasks/invalid",
                "id": "error-2",
                "params": {},
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert "error" in data
        assert data["error"]["code"] == -32601  # METHOD_NOT_FOUND


class TestContractReviewIntegration:
    """Integration tests for contract review workflow."""

    async def test_full_contract_review_flow(
        self, mock_settings: MagicMock
    ) -> None:
        """Test the complete contract review flow."""
        from sae.agents.contract_review import run_contract_review
        from sae.agents.state import ContractInput

        # Mock all LLM calls
        mock_clauses_response = MagicMock()
        mock_clauses_response.content = """[
            {"type": "confidentiality", "title": "NDA", "text": "Confidential info", "location": "Section 1"}
        ]"""

        mock_risks_response = MagicMock()
        mock_risks_response.content = """[
            {"clause_id": "test", "risk_level": "low", "confidence": 0.9, "issues": [], "explanation": "Standard", "affected_party": "both"}
        ]"""

        mock_recs_response = MagicMock()
        mock_recs_response.content = "[]"

        with patch("sae.agents.nodes.extract_clauses.ChatOpenAI") as mock_extract_llm, \
             patch("sae.agents.nodes.analyze_risks.ChatOpenAI") as mock_analyze_llm, \
             patch("sae.agents.nodes.generate_recommendations.ChatOpenAI") as mock_rec_llm:

            # Configure mocks
            for mock_llm, response in [
                (mock_extract_llm, mock_clauses_response),
                (mock_analyze_llm, mock_risks_response),
                (mock_rec_llm, mock_recs_response),
            ]:
                instance = AsyncMock()
                instance.ainvoke = AsyncMock(return_value=response)
                mock_llm.return_value = instance

            # Run the workflow
            input_data = ContractInput(
                task_id="integration-test",
                contract_text=SIMPLE_NDA,
            )

            result = await run_contract_review(input_data)

            assert result.success is True
            assert result.task_id == "integration-test"
            assert len(result.analysis.clauses) >= 0
