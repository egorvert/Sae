"""Tests for A2A protocol models."""

from datetime import datetime

import pytest
from pydantic import ValidationError

from sae.models.a2a import (
    AgentCapabilities,
    AgentCard,
    AgentSkill,
    Artifact,
    DataPart,
    FilePart,
    JsonRpcError,
    JsonRpcRequest,
    JsonRpcResponse,
    Message,
    Task,
    TaskCancelParams,
    TaskGetParams,
    TaskResult,
    TaskSendParams,
    TaskState,
    TaskStatus,
    TextPart,
)


class TestTaskState:
    """Tests for TaskState enum."""

    def test_task_state_values(self) -> None:
        """Test that TaskState has all expected values."""
        assert TaskState.SUBMITTED == "submitted"
        assert TaskState.WORKING == "working"
        assert TaskState.INPUT_REQUIRED == "input-required"
        assert TaskState.COMPLETED == "completed"
        assert TaskState.FAILED == "failed"
        assert TaskState.CANCELED == "canceled"

    def test_task_state_count(self) -> None:
        """Test that TaskState has exactly 6 states."""
        assert len(TaskState) == 6

    def test_task_state_is_string_enum(self) -> None:
        """Test that TaskState values are strings."""
        for state in TaskState:
            assert isinstance(state.value, str)


class TestTextPart:
    """Tests for TextPart model."""

    def test_text_part_creation(self) -> None:
        """Test creating a TextPart."""
        part = TextPart(text="Hello, world!")
        assert part.type == "text"
        assert part.text == "Hello, world!"

    def test_text_part_type_is_literal(self) -> None:
        """Test that TextPart type is always 'text'."""
        part = TextPart(text="Test")
        assert part.type == "text"

    def test_text_part_empty_text(self) -> None:
        """Test TextPart with empty text is valid."""
        part = TextPart(text="")
        assert part.text == ""


class TestFilePart:
    """Tests for FilePart model."""

    def test_file_part_creation(self) -> None:
        """Test creating a FilePart."""
        part = FilePart(file={"uri": "file://test.pdf", "mimeType": "application/pdf"})
        assert part.type == "file"
        assert part.file["uri"] == "file://test.pdf"

    def test_file_part_with_name(self) -> None:
        """Test FilePart with name."""
        part = FilePart(
            file={"uri": "file://contract.docx", "mimeType": "application/docx", "name": "contract.docx"}
        )
        assert part.file["name"] == "contract.docx"


class TestDataPart:
    """Tests for DataPart model."""

    def test_data_part_creation(self) -> None:
        """Test creating a DataPart."""
        part = DataPart(data={"key": "value", "count": 42})
        assert part.type == "data"
        assert part.data["key"] == "value"
        assert part.data["count"] == 42


class TestMessage:
    """Tests for Message model."""

    def test_message_user_role(self) -> None:
        """Test message with user role."""
        msg = Message(role="user", parts=[TextPart(text="Hello")])
        assert msg.role == "user"

    def test_message_agent_role(self) -> None:
        """Test message with agent role."""
        msg = Message(role="agent", parts=[TextPart(text="Response")])
        assert msg.role == "agent"

    def test_message_invalid_role_rejected(self) -> None:
        """Test that invalid roles are rejected."""
        with pytest.raises(ValidationError):
            Message(role="invalid", parts=[TextPart(text="Test")])  # type: ignore

    def test_message_multiple_parts(self) -> None:
        """Test message with multiple parts."""
        msg = Message(
            role="user",
            parts=[
                TextPart(text="See the attached:"),
                FilePart(file={"uri": "file://test.pdf"}),
            ],
        )
        assert len(msg.parts) == 2

    def test_message_default_metadata(self) -> None:
        """Test that metadata defaults to empty dict."""
        msg = Message(role="user", parts=[TextPart(text="Test")])
        assert msg.metadata == {}

    def test_message_with_metadata(self) -> None:
        """Test message with custom metadata."""
        msg = Message(
            role="user",
            parts=[TextPart(text="Test")],
            metadata={"source": "test", "priority": 1},
        )
        assert msg.metadata["source"] == "test"


class TestTaskStatus:
    """Tests for TaskStatus model."""

    def test_task_status_creation(self) -> None:
        """Test creating a TaskStatus."""
        status = TaskStatus(state=TaskState.SUBMITTED)
        assert status.state == TaskState.SUBMITTED
        assert status.message is None

    def test_task_status_with_message(self) -> None:
        """Test TaskStatus with a message."""
        msg = Message(role="agent", parts=[TextPart(text="Working on it...")])
        status = TaskStatus(state=TaskState.WORKING, message=msg)
        assert status.message is not None
        assert status.message.role == "agent"

    def test_task_status_default_timestamp(self) -> None:
        """Test that timestamp defaults to current time."""
        before = datetime.utcnow()
        status = TaskStatus(state=TaskState.SUBMITTED)
        after = datetime.utcnow()
        assert before <= status.timestamp <= after


class TestArtifact:
    """Tests for Artifact model."""

    def test_artifact_creation(self) -> None:
        """Test creating an Artifact."""
        artifact = Artifact(
            name="analysis_report",
            parts=[TextPart(text="# Report")],
        )
        assert artifact.name == "analysis_report"
        assert artifact.description is None
        assert artifact.index == 0

    def test_artifact_with_description(self) -> None:
        """Test Artifact with description."""
        artifact = Artifact(
            name="report",
            description="Complete analysis report",
            parts=[TextPart(text="Content")],
        )
        assert artifact.description == "Complete analysis report"

    def test_artifact_default_index(self) -> None:
        """Test that artifact index defaults to 0."""
        artifact = Artifact(name="test", parts=[])
        assert artifact.index == 0

    def test_artifact_custom_index(self) -> None:
        """Test artifact with custom index."""
        artifact = Artifact(name="test", parts=[], index=5)
        assert artifact.index == 5


class TestTask:
    """Tests for Task model."""

    def test_task_creation(self) -> None:
        """Test creating a Task."""
        task = Task(
            id="task-123",
            status=TaskStatus(state=TaskState.SUBMITTED),
        )
        assert task.id == "task-123"
        assert task.status.state == TaskState.SUBMITTED
        assert task.artifacts == []
        assert task.history == []
        assert task.metadata == {}

    def test_task_with_history(self) -> None:
        """Test task with message history."""
        msg = Message(role="user", parts=[TextPart(text="Review this contract")])
        task = Task(
            id="task-123",
            status=TaskStatus(state=TaskState.WORKING),
            history=[msg],
        )
        assert len(task.history) == 1
        assert task.history[0].role == "user"

    def test_task_with_artifacts(self) -> None:
        """Test task with artifacts."""
        artifact = Artifact(name="report", parts=[TextPart(text="Content")])
        task = Task(
            id="task-123",
            status=TaskStatus(state=TaskState.COMPLETED),
            artifacts=[artifact],
        )
        assert len(task.artifacts) == 1


class TestAgentCard:
    """Tests for AgentCard model."""

    def test_agent_card_creation(self) -> None:
        """Test creating an AgentCard."""
        card = AgentCard(
            name="Test Agent",
            description="A test agent",
            url="http://localhost:8000",
            version="0.1.0",
        )
        assert card.name == "Test Agent"
        assert card.description == "A test agent"
        assert card.url == "http://localhost:8000"

    def test_agent_card_default_capabilities(self) -> None:
        """Test default capabilities."""
        card = AgentCard(
            name="Test",
            description="Test",
            url="http://test",
            version="0.1.0",
        )
        assert card.capabilities.streaming is True
        assert card.capabilities.push_notifications is False
        assert card.capabilities.state_transition_history is False

    def test_agent_card_default_input_output_modes(self) -> None:
        """Test default input/output modes."""
        card = AgentCard(
            name="Test",
            description="Test",
            url="http://test",
            version="0.1.0",
        )
        assert card.default_input_modes == ["text"]
        assert card.default_output_modes == ["text"]

    def test_agent_card_with_skills(self) -> None:
        """Test AgentCard with skills."""
        skill = AgentSkill(
            id="contract_review",
            name="Contract Review",
            description="Analyze contracts",
        )
        card = AgentCard(
            name="Test",
            description="Test",
            url="http://test",
            version="0.1.0",
            skills=[skill],
        )
        assert len(card.skills) == 1
        assert card.skills[0].id == "contract_review"

    def test_agent_card_alias_serialization(self) -> None:
        """Test that aliases are used in serialization."""
        # Use alias names for construction when Field has alias defined
        caps = AgentCapabilities(**{"pushNotifications": True, "stateTransitionHistory": True})
        data = caps.model_dump(by_alias=True)
        assert "pushNotifications" in data
        assert "stateTransitionHistory" in data
        assert data["pushNotifications"] is True


class TestAgentSkill:
    """Tests for AgentSkill model."""

    def test_agent_skill_creation(self) -> None:
        """Test creating an AgentSkill."""
        skill = AgentSkill(
            id="review",
            name="Contract Review",
            description="Review contracts for risks",
        )
        assert skill.id == "review"
        assert skill.tags == []
        assert skill.examples == []

    def test_agent_skill_with_tags_and_examples(self) -> None:
        """Test AgentSkill with tags and examples."""
        skill = AgentSkill(
            id="review",
            name="Review",
            description="Description",
            tags=["legal", "contracts"],
            examples=["Review this NDA"],
        )
        assert skill.tags == ["legal", "contracts"]
        assert skill.examples == ["Review this NDA"]


class TestJsonRpcRequest:
    """Tests for JsonRpcRequest model."""

    def test_jsonrpc_request_creation(self) -> None:
        """Test creating a JsonRpcRequest."""
        req = JsonRpcRequest(method="tasks/send", id="req-1")
        assert req.jsonrpc == "2.0"
        assert req.method == "tasks/send"
        assert req.id == "req-1"
        assert req.params == {}

    def test_jsonrpc_request_with_params(self) -> None:
        """Test JsonRpcRequest with parameters."""
        req = JsonRpcRequest(
            method="tasks/send",
            id=123,
            params={"id": "task-1", "message": {"role": "user", "parts": []}},
        )
        assert req.params["id"] == "task-1"

    def test_jsonrpc_request_integer_id(self) -> None:
        """Test JsonRpcRequest with integer ID."""
        req = JsonRpcRequest(method="test", id=42)
        assert req.id == 42


class TestJsonRpcResponse:
    """Tests for JsonRpcResponse model."""

    def test_jsonrpc_response_with_result(self) -> None:
        """Test JsonRpcResponse with result."""
        resp = JsonRpcResponse(id="req-1", result={"success": True})
        assert resp.jsonrpc == "2.0"
        assert resp.result == {"success": True}
        assert resp.error is None

    def test_jsonrpc_response_with_error(self) -> None:
        """Test JsonRpcResponse with error."""
        error = JsonRpcError(code=-32600, message="Invalid Request")
        resp = JsonRpcResponse(id="req-1", error=error)
        assert resp.error is not None
        assert resp.error.code == -32600
        assert resp.result is None


class TestJsonRpcError:
    """Tests for JsonRpcError model."""

    def test_jsonrpc_error_creation(self) -> None:
        """Test creating a JsonRpcError."""
        error = JsonRpcError(code=-32700, message="Parse error")
        assert error.code == -32700
        assert error.message == "Parse error"
        assert error.data is None

    def test_jsonrpc_error_with_data(self) -> None:
        """Test JsonRpcError with additional data."""
        error = JsonRpcError(
            code=-32602,
            message="Invalid params",
            data={"missing": ["id"]},
        )
        assert error.data == {"missing": ["id"]}


class TestTaskSendParams:
    """Tests for TaskSendParams model."""

    def test_task_send_params_creation(self) -> None:
        """Test creating TaskSendParams."""
        msg = Message(role="user", parts=[TextPart(text="Test")])
        params = TaskSendParams(id="task-1", message=msg)
        assert params.id == "task-1"
        assert params.message.role == "user"
        assert params.metadata == {}

    def test_task_send_params_validation(self) -> None:
        """Test that TaskSendParams requires id and message."""
        with pytest.raises(ValidationError):
            TaskSendParams(id="test")  # type: ignore


class TestTaskGetParams:
    """Tests for TaskGetParams model."""

    def test_task_get_params_creation(self) -> None:
        """Test creating TaskGetParams."""
        params = TaskGetParams(id="task-1")
        assert params.id == "task-1"
        assert params.history_length is None

    def test_task_get_params_with_history_length(self) -> None:
        """Test TaskGetParams with history length."""
        # Use alias in constructor since Field has alias defined
        params = TaskGetParams(**{"id": "task-1", "historyLength": 10})
        assert params.history_length == 10

    def test_task_get_params_alias(self) -> None:
        """Test that historyLength alias works."""
        # Test deserialization with alias
        params = TaskGetParams.model_validate({"id": "task-1", "historyLength": 5})
        assert params.history_length == 5


class TestTaskCancelParams:
    """Tests for TaskCancelParams model."""

    def test_task_cancel_params_creation(self) -> None:
        """Test creating TaskCancelParams."""
        params = TaskCancelParams(id="task-1")
        assert params.id == "task-1"


class TestTaskResult:
    """Tests for TaskResult model."""

    def test_task_result_creation(self) -> None:
        """Test creating a TaskResult."""
        result = TaskResult(
            id="task-1",
            status=TaskStatus(state=TaskState.COMPLETED),
        )
        assert result.id == "task-1"
        assert result.status.state == TaskState.COMPLETED
        assert result.artifacts == []
        assert result.metadata == {}

    def test_task_result_with_artifacts(self) -> None:
        """Test TaskResult with artifacts."""
        artifact = Artifact(name="report", parts=[TextPart(text="Content")])
        result = TaskResult(
            id="task-1",
            status=TaskStatus(state=TaskState.COMPLETED),
            artifacts=[artifact],
        )
        assert len(result.artifacts) == 1
