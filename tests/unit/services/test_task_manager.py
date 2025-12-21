"""Tests for TaskManager service."""

import asyncio
from datetime import datetime

import pytest

from sae.models.a2a import (
    Artifact,
    Message,
    TaskState,
    TextPart,
)
from sae.services.task_manager import (
    InvalidStateTransitionError,
    TaskManager,
    TaskNotFoundError,
    VALID_TRANSITIONS,
    get_task_manager,
)


class TestValidTransitions:
    """Tests for VALID_TRANSITIONS constant."""

    def test_submitted_transitions(self) -> None:
        """Test valid transitions from SUBMITTED state."""
        assert VALID_TRANSITIONS[TaskState.SUBMITTED] == {
            TaskState.WORKING,
            TaskState.CANCELED,
            TaskState.FAILED,
        }

    def test_working_transitions(self) -> None:
        """Test valid transitions from WORKING state."""
        assert VALID_TRANSITIONS[TaskState.WORKING] == {
            TaskState.COMPLETED,
            TaskState.FAILED,
            TaskState.CANCELED,
            TaskState.INPUT_REQUIRED,
        }

    def test_input_required_transitions(self) -> None:
        """Test valid transitions from INPUT_REQUIRED state."""
        assert VALID_TRANSITIONS[TaskState.INPUT_REQUIRED] == {
            TaskState.WORKING,
            TaskState.CANCELED,
            TaskState.FAILED,
        }

    def test_terminal_states_have_no_transitions(self) -> None:
        """Test that terminal states have no valid transitions."""
        assert VALID_TRANSITIONS[TaskState.COMPLETED] == set()
        assert VALID_TRANSITIONS[TaskState.FAILED] == set()
        assert VALID_TRANSITIONS[TaskState.CANCELED] == set()


class TestTaskManagerCreateTask:
    """Tests for TaskManager.create_task method."""

    async def test_create_task_generates_id(self, task_manager: TaskManager) -> None:
        """Test that create_task generates a UUID when id is not provided."""
        message = Message(role="user", parts=[TextPart(text="Test")])
        task = await task_manager.create_task(message)

        assert task.id is not None
        assert len(task.id) == 36  # UUID format

    async def test_create_task_uses_provided_id(self, task_manager: TaskManager) -> None:
        """Test that create_task uses the provided task_id."""
        message = Message(role="user", parts=[TextPart(text="Test")])
        task = await task_manager.create_task(message, task_id="custom-id-123")

        assert task.id == "custom-id-123"

    async def test_create_task_initial_state_submitted(self, task_manager: TaskManager) -> None:
        """Test that new tasks start in SUBMITTED state."""
        message = Message(role="user", parts=[TextPart(text="Test")])
        task = await task_manager.create_task(message)

        assert task.status.state == TaskState.SUBMITTED

    async def test_create_task_stores_message_in_history(self, task_manager: TaskManager) -> None:
        """Test that the initial message is stored in history."""
        message = Message(role="user", parts=[TextPart(text="Review contract")])
        task = await task_manager.create_task(message)

        assert len(task.history) == 1
        assert task.history[0].role == "user"
        assert task.history[0].parts[0].text == "Review contract"  # type: ignore

    async def test_create_task_with_metadata(self, task_manager: TaskManager) -> None:
        """Test that metadata is stored correctly."""
        message = Message(role="user", parts=[TextPart(text="Test")])
        task = await task_manager.create_task(
            message,
            metadata={"source": "api", "priority": 1},
        )

        assert task.metadata["source"] == "api"
        assert task.metadata["priority"] == 1

    async def test_create_task_existing_id_appends_message(
        self, task_manager: TaskManager
    ) -> None:
        """Test that creating with existing id appends message to history."""
        msg1 = Message(role="user", parts=[TextPart(text="First message")])
        msg2 = Message(role="user", parts=[TextPart(text="Second message")])

        task1 = await task_manager.create_task(msg1, task_id="duplicate-id")
        task2 = await task_manager.create_task(msg2, task_id="duplicate-id")

        # Should return the same task
        assert task1.id == task2.id

        # History should have both messages
        assert len(task1.history) == 2
        assert task1.history[0].parts[0].text == "First message"  # type: ignore
        assert task1.history[1].parts[0].text == "Second message"  # type: ignore

    async def test_create_task_sets_timestamp(self, task_manager: TaskManager) -> None:
        """Test that task creation sets a timestamp."""
        before = datetime.utcnow()
        message = Message(role="user", parts=[TextPart(text="Test")])
        task = await task_manager.create_task(message)
        after = datetime.utcnow()

        assert before <= task.status.timestamp <= after


class TestTaskManagerGetTask:
    """Tests for TaskManager.get_task method."""

    async def test_get_task_success(self, task_manager: TaskManager) -> None:
        """Test getting an existing task."""
        message = Message(role="user", parts=[TextPart(text="Test")])
        created_task = await task_manager.create_task(message, task_id="get-test")

        retrieved_task = await task_manager.get_task("get-test")

        assert retrieved_task.id == created_task.id

    async def test_get_task_not_found(self, task_manager: TaskManager) -> None:
        """Test that getting a non-existent task raises TaskNotFoundError."""
        with pytest.raises(TaskNotFoundError) as exc_info:
            await task_manager.get_task("non-existent")

        assert "non-existent" in str(exc_info.value)


class TestTaskManagerUpdateStatus:
    """Tests for TaskManager.update_status method."""

    async def test_valid_transition_submitted_to_working(
        self, task_manager: TaskManager
    ) -> None:
        """Test SUBMITTED -> WORKING transition."""
        message = Message(role="user", parts=[TextPart(text="Test")])
        task = await task_manager.create_task(message)

        updated = await task_manager.update_status(task.id, TaskState.WORKING)

        assert updated.status.state == TaskState.WORKING

    async def test_valid_transition_working_to_completed(
        self, task_manager: TaskManager
    ) -> None:
        """Test WORKING -> COMPLETED transition."""
        message = Message(role="user", parts=[TextPart(text="Test")])
        task = await task_manager.create_task(message)
        await task_manager.update_status(task.id, TaskState.WORKING)

        updated = await task_manager.update_status(task.id, TaskState.COMPLETED)

        assert updated.status.state == TaskState.COMPLETED

    async def test_valid_transition_working_to_failed(
        self, task_manager: TaskManager
    ) -> None:
        """Test WORKING -> FAILED transition."""
        message = Message(role="user", parts=[TextPart(text="Test")])
        task = await task_manager.create_task(message)
        await task_manager.update_status(task.id, TaskState.WORKING)

        updated = await task_manager.update_status(task.id, TaskState.FAILED)

        assert updated.status.state == TaskState.FAILED

    async def test_valid_transition_working_to_canceled(
        self, task_manager: TaskManager
    ) -> None:
        """Test WORKING -> CANCELED transition."""
        message = Message(role="user", parts=[TextPart(text="Test")])
        task = await task_manager.create_task(message)
        await task_manager.update_status(task.id, TaskState.WORKING)

        updated = await task_manager.update_status(task.id, TaskState.CANCELED)

        assert updated.status.state == TaskState.CANCELED

    async def test_valid_transition_working_to_input_required(
        self, task_manager: TaskManager
    ) -> None:
        """Test WORKING -> INPUT_REQUIRED transition."""
        message = Message(role="user", parts=[TextPart(text="Test")])
        task = await task_manager.create_task(message)
        await task_manager.update_status(task.id, TaskState.WORKING)

        updated = await task_manager.update_status(task.id, TaskState.INPUT_REQUIRED)

        assert updated.status.state == TaskState.INPUT_REQUIRED

    async def test_invalid_transition_completed_to_working(
        self, task_manager: TaskManager
    ) -> None:
        """Test that COMPLETED -> WORKING is rejected."""
        message = Message(role="user", parts=[TextPart(text="Test")])
        task = await task_manager.create_task(message)
        await task_manager.update_status(task.id, TaskState.WORKING)
        await task_manager.update_status(task.id, TaskState.COMPLETED)

        with pytest.raises(InvalidStateTransitionError):
            await task_manager.update_status(task.id, TaskState.WORKING)

    async def test_invalid_transition_failed_to_completed(
        self, task_manager: TaskManager
    ) -> None:
        """Test that FAILED -> COMPLETED is rejected."""
        message = Message(role="user", parts=[TextPart(text="Test")])
        task = await task_manager.create_task(message)
        await task_manager.update_status(task.id, TaskState.WORKING)
        await task_manager.update_status(task.id, TaskState.FAILED)

        with pytest.raises(InvalidStateTransitionError):
            await task_manager.update_status(task.id, TaskState.COMPLETED)

    async def test_invalid_transition_canceled_to_working(
        self, task_manager: TaskManager
    ) -> None:
        """Test that CANCELED -> WORKING is rejected."""
        message = Message(role="user", parts=[TextPart(text="Test")])
        task = await task_manager.create_task(message)
        await task_manager.update_status(task.id, TaskState.CANCELED)

        with pytest.raises(InvalidStateTransitionError):
            await task_manager.update_status(task.id, TaskState.WORKING)

    async def test_update_status_with_message(self, task_manager: TaskManager) -> None:
        """Test that status update can include a message."""
        user_msg = Message(role="user", parts=[TextPart(text="Test")])
        task = await task_manager.create_task(user_msg)

        status_msg = Message(
            role="agent",
            parts=[TextPart(text="Processing...")],
        )
        updated = await task_manager.update_status(
            task.id, TaskState.WORKING, message=status_msg
        )

        assert updated.status.message is not None
        assert updated.status.message.role == "agent"
        assert len(updated.history) == 2

    async def test_update_status_not_found(self, task_manager: TaskManager) -> None:
        """Test that updating non-existent task raises TaskNotFoundError."""
        with pytest.raises(TaskNotFoundError):
            await task_manager.update_status("non-existent", TaskState.WORKING)

    async def test_update_status_updates_timestamp(
        self, task_manager: TaskManager
    ) -> None:
        """Test that update_status updates the timestamp."""
        message = Message(role="user", parts=[TextPart(text="Test")])
        task = await task_manager.create_task(message)
        original_timestamp = task.status.timestamp

        await asyncio.sleep(0.01)  # Small delay to ensure different timestamp

        updated = await task_manager.update_status(task.id, TaskState.WORKING)

        assert updated.status.timestamp > original_timestamp


class TestTaskManagerAddArtifact:
    """Tests for TaskManager.add_artifact method."""

    async def test_add_artifact_success(self, task_manager: TaskManager) -> None:
        """Test adding an artifact to a task."""
        message = Message(role="user", parts=[TextPart(text="Test")])
        task = await task_manager.create_task(message)

        artifact = Artifact(
            name="report",
            description="Analysis report",
            parts=[TextPart(text="# Report\n\nContent here...")],
        )
        updated = await task_manager.add_artifact(task.id, artifact)

        assert len(updated.artifacts) == 1
        assert updated.artifacts[0].name == "report"

    async def test_add_artifact_increments_index(self, task_manager: TaskManager) -> None:
        """Test that artifact index is auto-incremented."""
        message = Message(role="user", parts=[TextPart(text="Test")])
        task = await task_manager.create_task(message)

        artifact1 = Artifact(name="first", parts=[TextPart(text="First")])
        artifact2 = Artifact(name="second", parts=[TextPart(text="Second")])

        await task_manager.add_artifact(task.id, artifact1)
        await task_manager.add_artifact(task.id, artifact2)

        updated = await task_manager.get_task(task.id)
        assert updated.artifacts[0].index == 0
        assert updated.artifacts[1].index == 1

    async def test_add_artifact_not_found(self, task_manager: TaskManager) -> None:
        """Test that adding artifact to non-existent task raises error."""
        artifact = Artifact(name="test", parts=[])

        with pytest.raises(TaskNotFoundError):
            await task_manager.add_artifact("non-existent", artifact)


class TestTaskManagerConvenienceMethods:
    """Tests for TaskManager convenience methods."""

    async def test_cancel_task_success(self, task_manager: TaskManager) -> None:
        """Test cancel_task transitions to CANCELED state."""
        message = Message(role="user", parts=[TextPart(text="Test")])
        task = await task_manager.create_task(message)

        canceled = await task_manager.cancel_task(task.id)

        assert canceled.status.state == TaskState.CANCELED
        assert canceled.status.message is not None
        assert "canceled" in canceled.status.message.parts[0].text.lower()  # type: ignore

    async def test_cancel_task_from_terminal_fails(
        self, task_manager: TaskManager
    ) -> None:
        """Test that canceling a completed task raises error."""
        message = Message(role="user", parts=[TextPart(text="Test")])
        task = await task_manager.create_task(message)
        await task_manager.update_status(task.id, TaskState.WORKING)
        await task_manager.update_status(task.id, TaskState.COMPLETED)

        with pytest.raises(InvalidStateTransitionError):
            await task_manager.cancel_task(task.id)

    async def test_fail_task_success(self, task_manager: TaskManager) -> None:
        """Test fail_task transitions to FAILED state."""
        message = Message(role="user", parts=[TextPart(text="Test")])
        task = await task_manager.create_task(message)
        await task_manager.update_status(task.id, TaskState.WORKING)

        failed = await task_manager.fail_task(task.id, "Something went wrong")

        assert failed.status.state == TaskState.FAILED
        assert failed.status.message is not None
        assert "Something went wrong" in failed.status.message.parts[0].text  # type: ignore

    async def test_complete_task_success(self, task_manager: TaskManager) -> None:
        """Test complete_task transitions to COMPLETED state."""
        message = Message(role="user", parts=[TextPart(text="Test")])
        task = await task_manager.create_task(message)
        await task_manager.update_status(task.id, TaskState.WORKING)

        completed = await task_manager.complete_task(task.id)

        assert completed.status.state == TaskState.COMPLETED

    async def test_complete_task_with_message(self, task_manager: TaskManager) -> None:
        """Test complete_task with a completion message."""
        user_msg = Message(role="user", parts=[TextPart(text="Test")])
        task = await task_manager.create_task(user_msg)
        await task_manager.update_status(task.id, TaskState.WORKING)

        completion_msg = Message(
            role="agent",
            parts=[TextPart(text="Analysis complete!")],
        )
        completed = await task_manager.complete_task(task.id, message=completion_msg)

        assert completed.status.message is not None


class TestTaskManagerSubscribe:
    """Tests for TaskManager.subscribe method."""

    async def test_subscribe_yields_initial_state(
        self, task_manager: TaskManager
    ) -> None:
        """Test that subscribe yields the initial task state."""
        message = Message(role="user", parts=[TextPart(text="Test")])
        task = await task_manager.create_task(message)

        results = []
        async for result in task_manager.subscribe(task.id):
            results.append(result)
            # Cancel the task to end the subscription
            await task_manager.cancel_task(task.id)
            break

        assert len(results) >= 1
        assert results[0].status.state == TaskState.SUBMITTED

    async def test_subscribe_receives_updates(self, task_manager: TaskManager) -> None:
        """Test that subscription receives state updates."""
        message = Message(role="user", parts=[TextPart(text="Test")])
        task = await task_manager.create_task(message)

        results = []

        async def subscribe_and_collect() -> None:
            async for result in task_manager.subscribe(task.id):
                results.append(result)
                if result.status.state == TaskState.COMPLETED:
                    break

        # Start subscription in background
        subscription_task = asyncio.create_task(subscribe_and_collect())

        # Give subscription time to start
        await asyncio.sleep(0.01)

        # Update task status
        await task_manager.update_status(task.id, TaskState.WORKING)
        await task_manager.update_status(task.id, TaskState.COMPLETED)

        # Wait for subscription to complete
        await asyncio.wait_for(subscription_task, timeout=1.0)

        # Should have initial + updates
        assert len(results) >= 2
        states = [r.status.state for r in results]
        assert TaskState.SUBMITTED in states
        assert TaskState.COMPLETED in states

    async def test_subscribe_not_found(self, task_manager: TaskManager) -> None:
        """Test that subscribing to non-existent task raises error."""
        with pytest.raises(TaskNotFoundError):
            async for _ in task_manager.subscribe("non-existent"):
                pass

    async def test_subscribe_stops_on_terminal_state(
        self, task_manager: TaskManager
    ) -> None:
        """Test that subscription stops after terminal state."""
        message = Message(role="user", parts=[TextPart(text="Test")])
        task = await task_manager.create_task(message)

        results = []

        async def subscribe_and_collect() -> None:
            async for result in task_manager.subscribe(task.id):
                results.append(result)

        subscription_task = asyncio.create_task(subscribe_and_collect())
        await asyncio.sleep(0.01)

        await task_manager.update_status(task.id, TaskState.WORKING)
        await task_manager.update_status(task.id, TaskState.FAILED)

        # Subscription should complete after FAILED
        await asyncio.wait_for(subscription_task, timeout=1.0)

        # Verify subscription ended
        assert results[-1].status.state == TaskState.FAILED


class TestTaskManagerListTasks:
    """Tests for TaskManager.list_tasks method."""

    async def test_list_tasks_returns_all(self, task_manager: TaskManager) -> None:
        """Test that list_tasks returns all tasks."""
        msg = Message(role="user", parts=[TextPart(text="Test")])
        await task_manager.create_task(msg, task_id="task-1")
        await task_manager.create_task(msg, task_id="task-2")
        await task_manager.create_task(msg, task_id="task-3")

        tasks = await task_manager.list_tasks()

        assert len(tasks) == 3

    async def test_list_tasks_filter_by_state(self, task_manager: TaskManager) -> None:
        """Test filtering tasks by state."""
        msg = Message(role="user", parts=[TextPart(text="Test")])
        await task_manager.create_task(msg, task_id="submitted-1")
        await task_manager.create_task(msg, task_id="submitted-2")

        task3 = await task_manager.create_task(msg, task_id="working-1")
        await task_manager.update_status(task3.id, TaskState.WORKING)

        submitted_tasks = await task_manager.list_tasks(state=TaskState.SUBMITTED)
        working_tasks = await task_manager.list_tasks(state=TaskState.WORKING)

        assert len(submitted_tasks) == 2
        assert len(working_tasks) == 1

    async def test_list_tasks_respects_limit(self, task_manager: TaskManager) -> None:
        """Test that list_tasks respects the limit parameter."""
        msg = Message(role="user", parts=[TextPart(text="Test")])
        for i in range(10):
            await task_manager.create_task(msg, task_id=f"task-{i}")

        tasks = await task_manager.list_tasks(limit=5)

        assert len(tasks) == 5

    async def test_list_tasks_empty(self, task_manager: TaskManager) -> None:
        """Test list_tasks on empty manager."""
        tasks = await task_manager.list_tasks()
        assert tasks == []


class TestGetTaskManager:
    """Tests for get_task_manager singleton function."""

    def test_get_task_manager_returns_instance(self) -> None:
        """Test that get_task_manager returns a TaskManager instance."""
        # Reset the global instance for testing
        import sae.services.task_manager as tm_module

        tm_module._task_manager = None

        manager = get_task_manager()
        assert isinstance(manager, TaskManager)

    def test_get_task_manager_returns_same_instance(self) -> None:
        """Test that get_task_manager returns the same instance."""
        manager1 = get_task_manager()
        manager2 = get_task_manager()
        assert manager1 is manager2


class TestTaskManagerConcurrency:
    """Tests for TaskManager thread safety."""

    async def test_concurrent_task_creation(self, task_manager: TaskManager) -> None:
        """Test that concurrent task creation is safe."""

        async def create_task(task_id: str) -> None:
            msg = Message(role="user", parts=[TextPart(text=f"Task {task_id}")])
            await task_manager.create_task(msg, task_id=task_id)

        # Create 20 tasks concurrently
        tasks = [create_task(f"concurrent-{i}") for i in range(20)]
        await asyncio.gather(*tasks)

        # All tasks should be created
        all_tasks = await task_manager.list_tasks()
        assert len(all_tasks) == 20

    async def test_concurrent_status_updates(self, task_manager: TaskManager) -> None:
        """Test that concurrent status updates are safe."""
        msg = Message(role="user", parts=[TextPart(text="Test")])

        # Create multiple tasks
        task_ids = []
        for i in range(10):
            task = await task_manager.create_task(msg, task_id=f"update-{i}")
            task_ids.append(task.id)

        async def update_task(task_id: str) -> None:
            await task_manager.update_status(task_id, TaskState.WORKING)
            await task_manager.update_status(task_id, TaskState.COMPLETED)

        # Update all tasks concurrently
        tasks = [update_task(tid) for tid in task_ids]
        await asyncio.gather(*tasks)

        # All tasks should be completed
        for task_id in task_ids:
            task = await task_manager.get_task(task_id)
            assert task.status.state == TaskState.COMPLETED
