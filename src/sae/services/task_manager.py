"""Task Manager - handles A2A task lifecycle.

Manages task state transitions and storage.
For MVP, uses in-memory storage. Can be upgraded to Redis later.
"""

import asyncio
from collections.abc import AsyncIterator
from datetime import datetime
from typing import Any
from uuid import uuid4

import structlog

from sae.models.a2a import (
    Artifact,
    Message,
    Task,
    TaskResult,
    TaskState,
    TaskStatus,
    TextPart,
)

logger = structlog.get_logger()


class TaskNotFoundError(Exception):
    """Raised when a task is not found."""

    pass


class InvalidStateTransitionError(Exception):
    """Raised when an invalid state transition is attempted."""

    pass


# Valid state transitions
VALID_TRANSITIONS: dict[TaskState, set[TaskState]] = {
    TaskState.SUBMITTED: {TaskState.WORKING, TaskState.CANCELED, TaskState.FAILED},
    TaskState.WORKING: {
        TaskState.COMPLETED,
        TaskState.FAILED,
        TaskState.CANCELED,
        TaskState.INPUT_REQUIRED,
    },
    TaskState.INPUT_REQUIRED: {TaskState.WORKING, TaskState.CANCELED, TaskState.FAILED},
    TaskState.COMPLETED: set(),  # Terminal state
    TaskState.FAILED: set(),  # Terminal state
    TaskState.CANCELED: set(),  # Terminal state
}


class TaskManager:
    """Manages A2A tasks and their lifecycle."""

    def __init__(self) -> None:
        """Initialize the task manager."""
        self._tasks: dict[str, Task] = {}
        self._subscribers: dict[str, list[asyncio.Queue[TaskResult]]] = {}
        self._lock = asyncio.Lock()

    async def create_task(
        self,
        message: Message,
        task_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Task:
        """Create a new task.

        Args:
            message: The initial message for the task
            task_id: Optional task ID, generated if not provided
            metadata: Optional metadata for the task

        Returns:
            The created task
        """
        async with self._lock:
            if task_id is None:
                task_id = str(uuid4())

            if task_id in self._tasks:
                # Task already exists, add message to history
                existing_task = self._tasks[task_id]
                existing_task.history.append(message)
                return existing_task

            task = Task(
                id=task_id,
                status=TaskStatus(
                    state=TaskState.SUBMITTED,
                    timestamp=datetime.utcnow(),
                ),
                history=[message],
                metadata=metadata or {},
            )

            self._tasks[task_id] = task
            self._subscribers[task_id] = []

            logger.info("Task created", task_id=task_id)
            return task

    async def get_task(self, task_id: str) -> Task:
        """Get a task by ID.

        Args:
            task_id: The task ID

        Returns:
            The task

        Raises:
            TaskNotFoundError: If task is not found
        """
        if task_id not in self._tasks:
            raise TaskNotFoundError(f"Task {task_id} not found")
        return self._tasks[task_id]

    async def update_status(
        self,
        task_id: str,
        state: TaskState,
        message: Message | None = None,
    ) -> Task:
        """Update task status.

        Args:
            task_id: The task ID
            state: The new state
            message: Optional status message

        Returns:
            The updated task

        Raises:
            TaskNotFoundError: If task is not found
            InvalidStateTransitionError: If transition is invalid
        """
        async with self._lock:
            if task_id not in self._tasks:
                raise TaskNotFoundError(f"Task {task_id} not found")

            task = self._tasks[task_id]
            current_state = task.status.state

            # Validate state transition
            if state not in VALID_TRANSITIONS.get(current_state, set()):
                raise InvalidStateTransitionError(
                    f"Cannot transition from {current_state} to {state}"
                )

            task.status = TaskStatus(
                state=state,
                message=message,
                timestamp=datetime.utcnow(),
            )

            if message:
                task.history.append(message)

            logger.info(
                "Task status updated",
                task_id=task_id,
                old_state=current_state,
                new_state=state,
            )

            # Notify subscribers
            await self._notify_subscribers(task_id)

            return task

    async def add_artifact(
        self,
        task_id: str,
        artifact: Artifact,
    ) -> Task:
        """Add an artifact to a task.

        Args:
            task_id: The task ID
            artifact: The artifact to add

        Returns:
            The updated task
        """
        async with self._lock:
            if task_id not in self._tasks:
                raise TaskNotFoundError(f"Task {task_id} not found")

            task = self._tasks[task_id]
            artifact.index = len(task.artifacts)
            task.artifacts.append(artifact)

            logger.info(
                "Artifact added to task",
                task_id=task_id,
                artifact_name=artifact.name,
            )

            await self._notify_subscribers(task_id)

            return task

    async def cancel_task(self, task_id: str) -> Task:
        """Cancel a task.

        Args:
            task_id: The task ID

        Returns:
            The canceled task
        """
        return await self.update_status(
            task_id,
            TaskState.CANCELED,
            Message(
                role="agent",
                parts=[TextPart(text="Task was canceled by request.")],
            ),
        )

    async def fail_task(self, task_id: str, error_message: str) -> Task:
        """Mark a task as failed.

        Args:
            task_id: The task ID
            error_message: The error message

        Returns:
            The failed task
        """
        return await self.update_status(
            task_id,
            TaskState.FAILED,
            Message(
                role="agent",
                parts=[TextPart(text=f"Task failed: {error_message}")],
            ),
        )

    async def complete_task(
        self,
        task_id: str,
        message: Message | None = None,
    ) -> Task:
        """Mark a task as completed.

        Args:
            task_id: The task ID
            message: Optional completion message

        Returns:
            The completed task
        """
        return await self.update_status(task_id, TaskState.COMPLETED, message)

    async def subscribe(self, task_id: str) -> AsyncIterator[TaskResult]:
        """Subscribe to task updates.

        Args:
            task_id: The task ID

        Yields:
            Task results as they are produced
        """
        if task_id not in self._tasks:
            raise TaskNotFoundError(f"Task {task_id} not found")

        queue: asyncio.Queue[TaskResult] = asyncio.Queue()

        async with self._lock:
            self._subscribers[task_id].append(queue)

        try:
            # Send initial state
            task = self._tasks[task_id]
            yield self._task_to_result(task)

            # Stream updates until terminal state
            while True:
                result = await queue.get()
                yield result

                if result.status.state in {
                    TaskState.COMPLETED,
                    TaskState.FAILED,
                    TaskState.CANCELED,
                }:
                    break
        finally:
            async with self._lock:
                if task_id in self._subscribers:
                    self._subscribers[task_id].remove(queue)

    async def _notify_subscribers(self, task_id: str) -> None:
        """Notify all subscribers of a task update."""
        if task_id not in self._subscribers:
            return

        task = self._tasks[task_id]
        result = self._task_to_result(task)

        for queue in self._subscribers[task_id]:
            await queue.put(result)

    def _task_to_result(self, task: Task) -> TaskResult:
        """Convert a task to a result."""
        return TaskResult(
            id=task.id,
            status=task.status,
            artifacts=task.artifacts,
            metadata=task.metadata,
        )

    async def list_tasks(
        self,
        state: TaskState | None = None,
        limit: int = 100,
    ) -> list[Task]:
        """List all tasks, optionally filtered by state.

        Args:
            state: Optional state filter
            limit: Maximum number of tasks to return

        Returns:
            List of tasks
        """
        tasks = list(self._tasks.values())

        if state:
            tasks = [t for t in tasks if t.status.state == state]

        return tasks[:limit]


# Global task manager instance
_task_manager: TaskManager | None = None


def get_task_manager() -> TaskManager:
    """Get the global task manager instance."""
    global _task_manager
    if _task_manager is None:
        _task_manager = TaskManager()
    return _task_manager
