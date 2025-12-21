"""Tests for the JSON-RPC handler."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from sae.api.jsonrpc import (
    INTERNAL_ERROR,
    INVALID_PARAMS,
    INVALID_REQUEST,
    INVALID_STATE,
    METHOD_NOT_FOUND,
    PARSE_ERROR,
    TASK_NOT_FOUND,
    make_error_response,
    make_success_response,
)
from sae.models.a2a import TaskState


class TestErrorCodes:
    """Tests for JSON-RPC error codes."""

    def test_parse_error_code(self) -> None:
        """Test PARSE_ERROR code value."""
        assert PARSE_ERROR == -32700

    def test_invalid_request_code(self) -> None:
        """Test INVALID_REQUEST code value."""
        assert INVALID_REQUEST == -32600

    def test_method_not_found_code(self) -> None:
        """Test METHOD_NOT_FOUND code value."""
        assert METHOD_NOT_FOUND == -32601

    def test_invalid_params_code(self) -> None:
        """Test INVALID_PARAMS code value."""
        assert INVALID_PARAMS == -32602

    def test_internal_error_code(self) -> None:
        """Test INTERNAL_ERROR code value."""
        assert INTERNAL_ERROR == -32603

    def test_task_not_found_code(self) -> None:
        """Test TASK_NOT_FOUND code value."""
        assert TASK_NOT_FOUND == -32001

    def test_invalid_state_code(self) -> None:
        """Test INVALID_STATE code value."""
        assert INVALID_STATE == -32002


class TestMakeErrorResponse:
    """Tests for make_error_response function."""

    def test_makes_error_response(self) -> None:
        """Test creating an error response."""
        response = make_error_response("req-1", -32600, "Invalid Request")

        assert response.jsonrpc == "2.0"
        assert response.id == "req-1"
        assert response.error is not None
        assert response.error.code == -32600
        assert response.error.message == "Invalid Request"
        assert response.result is None

    def test_makes_error_response_with_data(self) -> None:
        """Test creating an error response with data."""
        response = make_error_response(
            "req-2", -32602, "Invalid params", data={"field": "id"}
        )

        assert response.error is not None
        assert response.error.data == {"field": "id"}


class TestMakeSuccessResponse:
    """Tests for make_success_response function."""

    def test_makes_success_response(self) -> None:
        """Test creating a success response."""
        response = make_success_response("req-1", {"id": "task-1"})

        assert response.jsonrpc == "2.0"
        assert response.id == "req-1"
        assert response.result == {"id": "task-1"}
        assert response.error is None


class TestHandleJsonrpcEndpoint:
    """Tests for POST /a2a endpoint."""

    def test_invalid_json_returns_parse_error(self, client: TestClient) -> None:
        """Test that invalid JSON returns PARSE_ERROR."""
        response = client.post(
            "/a2a",
            content="not valid json{",
            headers={"Content-Type": "application/json"},
        )
        data = response.json()

        assert data["error"]["code"] == PARSE_ERROR

    def test_wrong_jsonrpc_version_returns_invalid_request(
        self, client: TestClient
    ) -> None:
        """Test that wrong jsonrpc version returns INVALID_REQUEST."""
        response = client.post(
            "/a2a",
            json={"jsonrpc": "1.0", "method": "tasks/send", "id": "1"},
        )
        data = response.json()

        assert data["error"]["code"] == INVALID_REQUEST

    def test_missing_method_returns_invalid_request(
        self, client: TestClient
    ) -> None:
        """Test that missing method field returns INVALID_REQUEST."""
        response = client.post(
            "/a2a",
            json={"jsonrpc": "2.0", "id": "1"},
        )
        data = response.json()

        assert data["error"]["code"] == INVALID_REQUEST

    def test_unknown_method_returns_method_not_found(
        self, client: TestClient
    ) -> None:
        """Test that unknown method returns METHOD_NOT_FOUND."""
        response = client.post(
            "/a2a",
            json={
                "jsonrpc": "2.0",
                "method": "unknown/method",
                "id": "1",
            },
        )
        data = response.json()

        assert data["error"]["code"] == METHOD_NOT_FOUND

    def test_tasks_send_creates_task(
        self, client: TestClient, mock_settings: MagicMock
    ) -> None:
        """Test that tasks/send creates a new task."""
        # Mock the task manager with all async methods
        with patch("sae.api.jsonrpc.get_task_manager") as mock_get_tm:
            mock_task = MagicMock()
            mock_task.id = "new-task-123"
            mock_task.status.state = TaskState.SUBMITTED
            mock_task.status.timestamp.isoformat.return_value = "2024-01-01T12:00:00"
            mock_task.history = []
            mock_task.metadata = {}

            mock_tm = MagicMock()
            mock_tm.create_task = AsyncMock(return_value=mock_task)
            mock_tm.get_task = AsyncMock(return_value=mock_task)
            mock_tm.update_status = AsyncMock()
            mock_tm.fail_task = AsyncMock()
            mock_tm.complete_task = AsyncMock()
            mock_tm.add_artifact = AsyncMock()
            mock_get_tm.return_value = mock_tm

            response = client.post(
                "/a2a",
                json={
                    "jsonrpc": "2.0",
                    "method": "tasks/send",
                    "id": "req-1",
                    "params": {
                        "id": "task-123",
                        "message": {
                            "role": "user",
                            "parts": [{"type": "text", "text": "Test contract"}],
                        },
                    },
                },
            )

            assert response.status_code == 200
            data = response.json()
            assert "result" in data
            assert data["result"]["id"] == "new-task-123"

    def test_tasks_send_invalid_params_returns_error(
        self, client: TestClient
    ) -> None:
        """Test that tasks/send with invalid params returns error."""
        response = client.post(
            "/a2a",
            json={
                "jsonrpc": "2.0",
                "method": "tasks/send",
                "id": "req-1",
                "params": {
                    # Missing required fields
                },
            },
        )
        data = response.json()

        assert data["error"]["code"] == INVALID_PARAMS

    def test_tasks_get_returns_task(
        self, client: TestClient, mock_settings: MagicMock
    ) -> None:
        """Test that tasks/get returns task status."""
        with patch("sae.api.jsonrpc.get_task_manager") as mock_get_tm:
            mock_task = MagicMock()
            mock_task.id = "task-123"
            mock_task.status.state = TaskState.WORKING
            mock_task.status.timestamp.isoformat.return_value = "2024-01-01T12:00:00"
            mock_task.artifacts = []
            mock_task.history = []

            mock_tm = MagicMock()
            mock_tm.get_task = AsyncMock(return_value=mock_task)
            mock_get_tm.return_value = mock_tm

            response = client.post(
                "/a2a",
                json={
                    "jsonrpc": "2.0",
                    "method": "tasks/get",
                    "id": "req-2",
                    "params": {"id": "task-123"},
                },
            )

            data = response.json()
            assert "result" in data
            assert data["result"]["id"] == "task-123"
            assert data["result"]["status"]["state"] == "working"

    def test_tasks_get_not_found(
        self, client: TestClient, mock_settings: MagicMock
    ) -> None:
        """Test that tasks/get returns TASK_NOT_FOUND for missing task."""
        from sae.services.task_manager import TaskNotFoundError

        with patch("sae.api.jsonrpc.get_task_manager") as mock_get_tm:
            mock_tm = MagicMock()
            mock_tm.get_task = AsyncMock(
                side_effect=TaskNotFoundError("Task not found")
            )
            mock_get_tm.return_value = mock_tm

            response = client.post(
                "/a2a",
                json={
                    "jsonrpc": "2.0",
                    "method": "tasks/get",
                    "id": "req-3",
                    "params": {"id": "nonexistent"},
                },
            )

            data = response.json()
            assert data["error"]["code"] == TASK_NOT_FOUND

    def test_tasks_cancel_success(
        self, client: TestClient, mock_settings: MagicMock
    ) -> None:
        """Test that tasks/cancel cancels a task."""
        with patch("sae.api.jsonrpc.get_task_manager") as mock_get_tm:
            mock_task = MagicMock()
            mock_task.id = "task-123"
            mock_task.status.state = TaskState.CANCELED
            mock_task.status.timestamp.isoformat.return_value = "2024-01-01T12:05:00"

            mock_tm = MagicMock()
            mock_tm.cancel_task = AsyncMock(return_value=mock_task)
            mock_get_tm.return_value = mock_tm

            response = client.post(
                "/a2a",
                json={
                    "jsonrpc": "2.0",
                    "method": "tasks/cancel",
                    "id": "req-4",
                    "params": {"id": "task-123"},
                },
            )

            data = response.json()
            assert "result" in data
            assert data["result"]["status"]["state"] == "canceled"

    def test_tasks_cancel_invalid_state(
        self, client: TestClient, mock_settings: MagicMock
    ) -> None:
        """Test that canceling completed task returns INVALID_STATE."""
        from sae.services.task_manager import InvalidStateTransitionError

        with patch("sae.api.jsonrpc.get_task_manager") as mock_get_tm:
            mock_tm = MagicMock()
            mock_tm.cancel_task = AsyncMock(
                side_effect=InvalidStateTransitionError("Cannot cancel")
            )
            mock_get_tm.return_value = mock_tm

            response = client.post(
                "/a2a",
                json={
                    "jsonrpc": "2.0",
                    "method": "tasks/cancel",
                    "id": "req-5",
                    "params": {"id": "completed-task"},
                },
            )

            data = response.json()
            assert data["error"]["code"] == INVALID_STATE

    def test_internal_error_handling(
        self, client: TestClient, mock_settings: MagicMock
    ) -> None:
        """Test that unexpected errors return INTERNAL_ERROR."""
        with patch("sae.api.jsonrpc.get_task_manager") as mock_get_tm:
            mock_tm = MagicMock()
            mock_tm.get_task = AsyncMock(side_effect=RuntimeError("Unexpected"))
            mock_get_tm.return_value = mock_tm

            response = client.post(
                "/a2a",
                json={
                    "jsonrpc": "2.0",
                    "method": "tasks/get",
                    "id": "req-6",
                    "params": {"id": "task-123"},
                },
            )

            data = response.json()
            assert data["error"]["code"] == INTERNAL_ERROR
