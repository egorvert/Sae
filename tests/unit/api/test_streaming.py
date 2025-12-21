"""Tests for SSE streaming endpoint."""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from sae.api.streaming import format_task_event
from sae.models.a2a import TaskResult, TaskState, TaskStatus


class TestFormatTaskEvent:
    """Tests for format_task_event function."""

    def test_format_task_event_structure(self) -> None:
        """Test that format_task_event returns correct structure."""
        result = TaskResult(
            id="task-123",
            status=TaskStatus(state=TaskState.WORKING),
        )

        event = format_task_event(result)

        assert event["event"] == "task_update"
        assert "data" in event
        # data is a JSON string, parse it
        data = json.loads(event["data"])
        assert "jsonrpc" in data
        assert data["jsonrpc"] == "2.0"

    def test_format_task_event_includes_result(self) -> None:
        """Test that format_task_event includes task result."""
        result = TaskResult(
            id="task-123",
            status=TaskStatus(state=TaskState.COMPLETED),
        )

        event = format_task_event(result)
        data = json.loads(event["data"])

        assert "result" in data
        assert data["result"]["id"] == "task-123"
        assert data["result"]["status"]["state"] == "completed"

    def test_format_task_event_with_artifacts(self) -> None:
        """Test that format_task_event includes artifacts."""
        from sae.models.a2a import Artifact, TextPart

        artifact = Artifact(
            name="report",
            parts=[TextPart(text="Content")],
        )
        result = TaskResult(
            id="task-123",
            status=TaskStatus(state=TaskState.COMPLETED),
            artifacts=[artifact],
        )

        event = format_task_event(result)
        data = json.loads(event["data"])

        assert len(data["result"]["artifacts"]) == 1
        assert data["result"]["artifacts"][0]["name"] == "report"


class TestStreamTaskEndpoint:
    """Tests for GET /a2a/stream/{task_id} endpoint."""

    # Note: SSE streaming tests are complex with TestClient
    # These would be better tested with async integration tests
    pass
