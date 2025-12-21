"""Global test fixtures for the Sae Legal Agent test suite."""

import asyncio
from collections.abc import AsyncIterator, Iterator
from datetime import datetime
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from sae.models.a2a import (
    Artifact,
    Message,
    Task,
    TaskResult,
    TaskState,
    TaskStatus,
    TextPart,
)
from sae.models.clauses import (
    ClauseType,
    ExtractedClause,
    Recommendation,
    RiskAssessment,
    RiskLevel,
)
from sae.services.task_manager import TaskManager

from .fixtures.sample_contracts import SIMPLE_NDA
from .fixtures.mock_llm_responses import (
    MOCK_CLAUSE_EXTRACTION_JSON,
    MOCK_RISK_ANALYSIS_JSON,
    MOCK_RECOMMENDATIONS_JSON,
)


# =============================================================================
# Event Loop Fixture
# =============================================================================


@pytest.fixture(scope="session")
def event_loop() -> Iterator[asyncio.AbstractEventLoop]:
    """Create an event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


# =============================================================================
# Settings Fixtures
# =============================================================================


@pytest.fixture
def mock_settings() -> Iterator[MagicMock]:
    """Create mock settings for testing.

    This fixture patches the get_settings function to return a mock settings
    object with test values, avoiding the need for actual environment variables.
    """
    from sae.config import get_settings

    # Clear the lru_cache before mocking
    get_settings.cache_clear()

    with patch("sae.config.get_settings") as mock_get_settings:
        settings = MagicMock()
        settings.openai_api_key = "test-openai-api-key"
        settings.pinecone_api_key = None  # Optional - not required
        settings.pinecone_index_name = "test-index"
        settings.api_key = None  # Auth disabled by default
        settings.rate_limit_enabled = False  # Disable for tests
        settings.rate_limit_per_minute = 30
        settings.cors_origins = ["*"]
        settings.log_level = "DEBUG"
        settings.environment = "development"
        settings.host = "0.0.0.0"
        settings.port = 8000
        settings.agent_name = "Test Legal Agent"
        settings.agent_version = "0.1.0-test"
        settings.agent_description = "Test agent for contract review"
        settings.is_production = False

        mock_get_settings.return_value = settings
        yield settings

    # Clear cache after test too
    get_settings.cache_clear()


@pytest.fixture
def mock_production_settings() -> Iterator[MagicMock]:
    """Create mock settings for production environment testing."""
    from sae.config import get_settings

    # Clear the lru_cache before mocking
    get_settings.cache_clear()

    with patch("sae.config.get_settings") as mock_get_settings:
        settings = MagicMock()
        settings.openai_api_key = "prod-api-key"
        settings.pinecone_api_key = None  # Optional
        settings.pinecone_index_name = "prod-index"
        settings.api_key = "prod-api-key-secret"  # Auth enabled
        settings.rate_limit_enabled = True
        settings.rate_limit_per_minute = 30
        settings.cors_origins = ["https://example.com"]  # Specific origins
        settings.log_level = "INFO"
        settings.environment = "production"
        settings.host = "0.0.0.0"
        settings.port = 8000
        settings.agent_name = "Sae Legal Agent"
        settings.agent_version = "0.1.0"
        settings.agent_description = "Contract clause review and risk analysis"
        settings.is_production = True

        mock_get_settings.return_value = settings
        yield settings

    # Clear cache after test too
    get_settings.cache_clear()


# =============================================================================
# Task Manager Fixtures
# =============================================================================


@pytest.fixture
def task_manager() -> TaskManager:
    """Create a fresh TaskManager instance for testing."""
    return TaskManager()


@pytest.fixture
def mock_task_manager() -> Iterator[MagicMock]:
    """Create a mock TaskManager for API testing."""
    manager = MagicMock(spec=TaskManager)
    manager.create_task = AsyncMock()
    manager.get_task = AsyncMock()
    manager.update_status = AsyncMock()
    manager.add_artifact = AsyncMock()
    manager.cancel_task = AsyncMock()
    manager.fail_task = AsyncMock()
    manager.complete_task = AsyncMock()
    manager.subscribe = AsyncMock()
    manager.list_tasks = AsyncMock()
    yield manager


# =============================================================================
# Message and Task Fixtures
# =============================================================================


@pytest.fixture
def sample_text_part() -> TextPart:
    """Create a sample TextPart."""
    return TextPart(text="Sample text content for testing.")


@pytest.fixture
def sample_user_message() -> Message:
    """Create a sample user message."""
    return Message(
        role="user",
        parts=[TextPart(text=SIMPLE_NDA)],
    )


@pytest.fixture
def sample_agent_message() -> Message:
    """Create a sample agent message."""
    return Message(
        role="agent",
        parts=[TextPart(text="I have analyzed the contract and found 3 clauses.")],
    )


@pytest.fixture
def sample_task_status() -> TaskStatus:
    """Create a sample task status."""
    return TaskStatus(
        state=TaskState.SUBMITTED,
        timestamp=datetime(2024, 1, 1, 12, 0, 0),
    )


@pytest.fixture
def sample_artifact() -> Artifact:
    """Create a sample artifact."""
    return Artifact(
        name="contract_analysis",
        description="Complete contract analysis results",
        parts=[TextPart(text="# Analysis Report\n\nAnalyzed 5 clauses...")],
        index=0,
    )


@pytest.fixture
def sample_task(sample_user_message: Message, sample_task_status: TaskStatus) -> Task:
    """Create a sample task."""
    return Task(
        id="task-12345",
        status=sample_task_status,
        history=[sample_user_message],
        artifacts=[],
        metadata={"source": "test"},
    )


@pytest.fixture
def completed_task(sample_task: Task, sample_artifact: Artifact) -> Task:
    """Create a completed task with artifacts."""
    sample_task.status = TaskStatus(
        state=TaskState.COMPLETED,
        timestamp=datetime(2024, 1, 1, 12, 5, 0),
    )
    sample_task.artifacts = [sample_artifact]
    return sample_task


# =============================================================================
# Clause Analysis Fixtures
# =============================================================================


@pytest.fixture
def sample_clause() -> ExtractedClause:
    """Create a sample extracted clause."""
    return ExtractedClause(
        id="clause-001",
        type=ClauseType.LIABILITY,
        title="Limitation of Liability",
        text="The company shall not be liable for any indirect damages.",
        location="Section 5.1",
    )


@pytest.fixture
def sample_clauses() -> list[ExtractedClause]:
    """Create a list of sample clauses."""
    return [
        ExtractedClause(
            id="clause-001",
            type=ClauseType.CONFIDENTIALITY,
            title="Confidentiality",
            text="All information shared shall remain confidential.",
            location="Section 1",
        ),
        ExtractedClause(
            id="clause-002",
            type=ClauseType.LIABILITY,
            title="Limitation of Liability",
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


@pytest.fixture
def sample_risk() -> RiskAssessment:
    """Create a sample risk assessment."""
    return RiskAssessment(
        clause_id="clause-001",
        risk_level=RiskLevel.HIGH,
        confidence=0.85,
        issues=["Unlimited liability exposure", "One-sided protection"],
        explanation="This clause exposes the client to significant risk.",
        affected_party="client",
    )


@pytest.fixture
def sample_risks() -> list[RiskAssessment]:
    """Create a list of sample risk assessments."""
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
            explanation="Liability cap may be insufficient for large claims.",
            affected_party="client",
        ),
        RiskAssessment(
            clause_id="clause-003",
            risk_level=RiskLevel.MEDIUM,
            confidence=0.78,
            issues=["Short notice period"],
            explanation="30 days may not be enough transition time.",
            affected_party="client",
        ),
    ]


@pytest.fixture
def sample_recommendation() -> Recommendation:
    """Create a sample recommendation."""
    return Recommendation(
        clause_id="clause-001",
        priority=1,
        action="Add mutual liability cap",
        rationale="Limits exposure for both parties.",
        suggested_text="Total liability shall not exceed $5,000,000.",
        risk_reduction=RiskLevel.MEDIUM,
    )


@pytest.fixture
def sample_recommendations() -> list[Recommendation]:
    """Create a list of sample recommendations."""
    return [
        Recommendation(
            clause_id="clause-002",
            priority=1,
            action="Increase liability cap",
            rationale="Current cap is too low for enterprise use.",
            suggested_text="Total liability shall not exceed $5,000,000.",
            risk_reduction=RiskLevel.LOW,
        ),
        Recommendation(
            clause_id="clause-003",
            priority=2,
            action="Extend notice period",
            rationale="Provides adequate transition time.",
            suggested_text="Either party may terminate with 90 days notice.",
            risk_reduction=RiskLevel.LOW,
        ),
    ]


# =============================================================================
# LLM Mock Fixtures
# =============================================================================


def _create_mock_llm_response(content: str) -> MagicMock:
    """Helper to create a mock LLM response."""
    response = MagicMock()
    response.content = content
    return response


@pytest.fixture
def mock_llm_clause_extraction() -> Iterator[AsyncMock]:
    """Mock LLM for clause extraction tests."""
    with patch("sae.agents.nodes.extract_clauses.ChatOpenAI") as MockLLM:
        mock_instance = AsyncMock()
        mock_instance.ainvoke = AsyncMock(
            return_value=_create_mock_llm_response(MOCK_CLAUSE_EXTRACTION_JSON)
        )
        MockLLM.return_value = mock_instance
        yield mock_instance


@pytest.fixture
def mock_llm_risk_analysis() -> Iterator[AsyncMock]:
    """Mock LLM for risk analysis tests."""
    with patch("sae.agents.nodes.analyze_risks.ChatOpenAI") as MockLLM:
        mock_instance = AsyncMock()
        mock_instance.ainvoke = AsyncMock(
            return_value=_create_mock_llm_response(MOCK_RISK_ANALYSIS_JSON)
        )
        MockLLM.return_value = mock_instance
        yield mock_instance


@pytest.fixture
def mock_llm_recommendations() -> Iterator[AsyncMock]:
    """Mock LLM for recommendation generation tests."""
    with patch("sae.agents.nodes.generate_recommendations.ChatOpenAI") as MockLLM:
        mock_instance = AsyncMock()
        mock_instance.ainvoke = AsyncMock(
            return_value=_create_mock_llm_response(MOCK_RECOMMENDATIONS_JSON)
        )
        MockLLM.return_value = mock_instance
        yield mock_instance


@pytest.fixture
def mock_all_llms(
    mock_llm_clause_extraction: AsyncMock,
    mock_llm_risk_analysis: AsyncMock,
    mock_llm_recommendations: AsyncMock,
) -> dict[str, AsyncMock]:
    """Mock all LLM calls for full workflow tests."""
    return {
        "extraction": mock_llm_clause_extraction,
        "analysis": mock_llm_risk_analysis,
        "recommendations": mock_llm_recommendations,
    }


# =============================================================================
# FastAPI Test Client Fixtures
# =============================================================================


@pytest.fixture
def app(mock_settings: MagicMock) -> Any:
    """Create a test FastAPI application.

    Note: Must import after mock_settings is applied to avoid
    loading real environment variables.
    """
    from sae.main import app
    return app


@pytest.fixture
def client(app: Any) -> TestClient:
    """Create a synchronous test client."""
    return TestClient(app)


# =============================================================================
# Utility Fixtures
# =============================================================================


@pytest.fixture
def contract_text() -> str:
    """Return the simple NDA contract text."""
    return SIMPLE_NDA


@pytest.fixture
def task_id() -> str:
    """Return a test task ID."""
    return "test-task-12345"


# =============================================================================
# File Part Fixtures (for document parsing tests)
# =============================================================================


@pytest.fixture
def sample_file_part_text() -> dict[str, Any]:
    """Create a sample text file part."""
    from tests.fixtures.sample_files import create_text_file_part
    return create_text_file_part("contract.txt")


@pytest.fixture
def sample_file_part_pdf() -> dict[str, Any]:
    """Create a sample PDF file part (minimal valid PDF)."""
    from tests.fixtures.sample_files import create_pdf_file_part
    return create_pdf_file_part("contract.pdf")


# =============================================================================
# Settings with Auth Fixtures
# =============================================================================


@pytest.fixture
def mock_settings_with_auth() -> Iterator[MagicMock]:
    """Create mock settings with API key authentication enabled."""
    from sae.config import get_settings

    # Clear the lru_cache before mocking
    get_settings.cache_clear()

    with patch("sae.config.get_settings") as mock_get_settings:
        settings = MagicMock()
        settings.openai_api_key = "test-openai-api-key"
        settings.pinecone_api_key = None  # Optional
        settings.pinecone_index_name = "test-index"
        settings.api_key = "test-api-key-12345"  # Auth enabled
        settings.rate_limit_enabled = True
        settings.rate_limit_per_minute = 30
        settings.cors_origins = ["*"]
        settings.log_level = "DEBUG"
        settings.environment = "development"
        settings.host = "0.0.0.0"
        settings.port = 8000
        settings.agent_name = "Test Legal Agent"
        settings.agent_version = "0.1.0-test"
        settings.agent_description = "Test agent for contract review"
        settings.is_production = False

        mock_get_settings.return_value = settings
        yield settings

    # Clear cache after test too
    get_settings.cache_clear()


@pytest.fixture
def mock_settings_no_auth() -> Iterator[MagicMock]:
    """Create mock settings with API key authentication disabled."""
    from sae.config import get_settings

    # Clear the lru_cache before mocking
    get_settings.cache_clear()

    with patch("sae.config.get_settings") as mock_get_settings:
        settings = MagicMock()
        settings.openai_api_key = "test-openai-api-key"
        settings.pinecone_api_key = None  # Optional
        settings.pinecone_index_name = "test-index"
        settings.api_key = None  # Auth disabled
        settings.rate_limit_enabled = False  # Disable rate limiting for tests
        settings.rate_limit_per_minute = 30
        settings.cors_origins = ["*"]
        settings.log_level = "DEBUG"
        settings.environment = "development"
        settings.host = "0.0.0.0"
        settings.port = 8000
        settings.agent_name = "Test Legal Agent"
        settings.agent_version = "0.1.0-test"
        settings.agent_description = "Test agent for contract review"
        settings.is_production = False

        mock_get_settings.return_value = settings
        yield settings

    # Clear cache after test too
    get_settings.cache_clear()
