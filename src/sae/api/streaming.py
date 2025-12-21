"""A2A SSE Streaming endpoint.

Implements Server-Sent Events for real-time task updates.
"""

import json
from collections.abc import AsyncIterator

import structlog
from fastapi import APIRouter
from sse_starlette.sse import EventSourceResponse

from sae.models.a2a import TaskResult
from sae.services.task_manager import TaskNotFoundError, get_task_manager

logger = structlog.get_logger()
router = APIRouter()


async def task_event_generator(task_id: str) -> AsyncIterator[dict]:
    """Generate SSE events for a task.

    Args:
        task_id: The task ID to stream updates for

    Yields:
        SSE event dictionaries
    """
    task_manager = get_task_manager()

    try:
        async for result in task_manager.subscribe(task_id):
            yield format_task_event(result)
    except TaskNotFoundError:
        yield {
            "event": "error",
            "data": json.dumps({"error": f"Task {task_id} not found"}),
        }


def format_task_event(result: TaskResult) -> dict:
    """Format a task result as an SSE event.

    Args:
        result: The task result to format

    Returns:
        SSE event dictionary
    """
    data = {
        "jsonrpc": "2.0",
        "result": {
            "id": result.id,
            "status": {
                "state": result.status.state.value,
                "timestamp": result.status.timestamp.isoformat(),
            },
        },
    }

    # Include message if present
    if result.status.message:
        data["result"]["status"]["message"] = {
            "role": result.status.message.role,
            "parts": [p.model_dump() for p in result.status.message.parts],
        }

    # Include artifacts if present
    if result.artifacts:
        data["result"]["artifacts"] = [
            {
                "name": a.name,
                "description": a.description,
                "parts": [p.model_dump() for p in a.parts],
                "index": a.index,
            }
            for a in result.artifacts
        ]

    return {
        "event": "task_update",
        "data": json.dumps(data),
    }


@router.get("/a2a/stream/{task_id}")
async def stream_task(task_id: str) -> EventSourceResponse:
    """Stream task updates via SSE.

    This endpoint allows clients to receive real-time updates
    about task progress using Server-Sent Events.

    Args:
        task_id: The task ID to stream updates for

    Returns:
        SSE response with task updates
    """
    logger.info("SSE stream started", task_id=task_id)

    return EventSourceResponse(
        task_event_generator(task_id),
        media_type="text/event-stream",
    )


@router.post("/a2a/sendSubscribe")
async def send_and_subscribe(
    # This is a simplified version - full implementation would parse JSON-RPC
) -> EventSourceResponse:
    """Send a message and subscribe to updates.

    This combines tasks/send with streaming - creates a task
    and immediately starts streaming updates.

    For full implementation, this should:
    1. Parse JSON-RPC request
    2. Create/update task
    3. Start processing
    4. Return SSE stream of updates
    """
    # TODO: Implement full tasks/sendSubscribe
    # For now, clients should use POST /a2a then GET /a2a/stream/{task_id}
    raise NotImplementedError(
        "Use POST /a2a with tasks/send, then GET /a2a/stream/{task_id}"
    )
