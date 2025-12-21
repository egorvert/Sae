"""A2A JSON-RPC 2.0 Handler.

Implements the A2A protocol JSON-RPC methods:
- tasks/send: Send a message and create/update a task
- tasks/sendSubscribe: Same as send but returns streaming response
- tasks/get: Get task status
- tasks/cancel: Cancel a task
"""

from typing import Any

import structlog
from fastapi import APIRouter, BackgroundTasks, Request
from pydantic import ValidationError
from slowapi import Limiter
from slowapi.util import get_remote_address

from sae.agents.contract_review import run_contract_review
from sae.agents.state import ContractInput
from sae.api.dependencies import ApiKeyDep
from sae.config import get_settings
from sae.models.a2a import (
    Artifact,
    JsonRpcError,
    JsonRpcRequest,
    JsonRpcResponse,
    Message,
    TaskCancelParams,
    TaskGetParams,
    TaskSendParams,
    TaskState,
    TextPart,
)
from sae.services.document_parser import (
    DocumentParserError,
    UnsupportedFileTypeError,
    parse_document,
)
from sae.services.task_manager import (
    InvalidStateTransitionError,
    TaskNotFoundError,
    get_task_manager,
)

logger = structlog.get_logger()
router = APIRouter()

# Rate limiter for this router
limiter = Limiter(key_func=get_remote_address)


# JSON-RPC Error Codes
PARSE_ERROR = -32700
INVALID_REQUEST = -32600
METHOD_NOT_FOUND = -32601
INVALID_PARAMS = -32602
INTERNAL_ERROR = -32603
TASK_NOT_FOUND = -32001
INVALID_STATE = -32002


def make_error_response(
    request_id: str | int,
    code: int,
    message: str,
    data: Any = None,
) -> JsonRpcResponse:
    """Create a JSON-RPC error response."""
    return JsonRpcResponse(
        id=request_id,
        error=JsonRpcError(code=code, message=message, data=data),
    )


def make_success_response(
    request_id: str | int,
    result: Any,
) -> JsonRpcResponse:
    """Create a JSON-RPC success response."""
    return JsonRpcResponse(id=request_id, result=result)


async def handle_tasks_send(
    params: dict[str, Any],
    background_tasks: BackgroundTasks,
) -> dict[str, Any]:
    """Handle tasks/send method.

    Creates or updates a task and processes it.
    """
    try:
        send_params = TaskSendParams(**params)
    except ValidationError as e:
        raise ValueError(f"Invalid parameters: {e}")

    task_manager = get_task_manager()

    # Create or get task
    task = await task_manager.create_task(
        message=send_params.message,
        task_id=send_params.id,
        metadata=send_params.metadata,
    )

    # Start processing in background
    background_tasks.add_task(process_task, task.id)

    return {
        "id": task.id,
        "status": {
            "state": task.status.state.value,
            "timestamp": task.status.timestamp.isoformat(),
        },
    }


async def handle_tasks_get(params: dict[str, Any]) -> dict[str, Any]:
    """Handle tasks/get method.

    Returns the current status of a task.
    """
    try:
        get_params = TaskGetParams(**params)
    except ValidationError as e:
        raise ValueError(f"Invalid parameters: {e}")

    task_manager = get_task_manager()
    task = await task_manager.get_task(get_params.id)

    result = {
        "id": task.id,
        "status": {
            "state": task.status.state.value,
            "timestamp": task.status.timestamp.isoformat(),
        },
        "artifacts": [
            {
                "name": a.name,
                "description": a.description,
                "parts": [p.model_dump() for p in a.parts],
                "index": a.index,
            }
            for a in task.artifacts
        ],
    }

    # Include history if requested
    if get_params.history_length:
        history_slice = task.history[-get_params.history_length :]
        result["history"] = [
            {
                "role": m.role,
                "parts": [p.model_dump() for p in m.parts],
            }
            for m in history_slice
        ]

    return result


async def handle_tasks_cancel(params: dict[str, Any]) -> dict[str, Any]:
    """Handle tasks/cancel method.

    Cancels a running task.
    """
    try:
        cancel_params = TaskCancelParams(**params)
    except ValidationError as e:
        raise ValueError(f"Invalid parameters: {e}")

    task_manager = get_task_manager()
    task = await task_manager.cancel_task(cancel_params.id)

    return {
        "id": task.id,
        "status": {
            "state": task.status.state.value,
            "timestamp": task.status.timestamp.isoformat(),
        },
    }


async def process_task(task_id: str) -> None:
    """Process a task in the background using the LangGraph agent."""
    task_manager = get_task_manager()

    try:
        # Transition to working
        await task_manager.update_status(task_id, TaskState.WORKING)
        logger.info("Task processing started", task_id=task_id)

        # Get the task to extract the contract text
        task = await task_manager.get_task(task_id)

        # Extract contract text from messages (text parts + file parts)
        contract_parts: list[str] = []

        for msg in task.history:
            if msg.role == "user":
                for part in msg.parts:
                    if hasattr(part, "text"):
                        # TextPart - add directly
                        contract_parts.append(part.text)
                    elif hasattr(part, "file"):
                        # FilePart - parse document and extract text
                        try:
                            file_text = await parse_document(part.file)
                            contract_parts.append(file_text)
                            logger.info(
                                "File parsed successfully",
                                task_id=task_id,
                                filename=part.file.get("name", "unknown"),
                            )
                        except UnsupportedFileTypeError as e:
                            logger.warning(
                                "Skipping unsupported file",
                                task_id=task_id,
                                error=str(e),
                            )
                        except DocumentParserError as e:
                            logger.error(
                                "Failed to parse file",
                                task_id=task_id,
                                error=str(e),
                            )
                            await task_manager.fail_task(
                                task_id, f"Failed to parse uploaded file: {e}"
                            )
                            return

        contract_text = "\n\n".join(contract_parts)

        if not contract_text.strip():
            await task_manager.fail_task(task_id, "No contract text provided")
            return

        # Run the contract review agent
        input_data = ContractInput(
            task_id=task_id,
            contract_text=contract_text.strip(),
            metadata=task.metadata,
        )

        result = await run_contract_review(input_data)

        if not result.success:
            await task_manager.fail_task(task_id, result.error or "Analysis failed")
            return

        # Create artifact with the analysis results
        analysis = result.analysis
        artifact = Artifact(
            name="contract_analysis",
            description="Complete contract clause analysis with risks and recommendations",
            parts=[
                TextPart(
                    text=f"""# Contract Analysis Report

## Summary
{analysis.summary}

## Overall Risk Level: {analysis.overall_risk.value.upper()}

## Clauses Analyzed ({len(analysis.clauses)})
{chr(10).join(f"- **{c.title}** ({c.type.value}): {c.location}" for c in analysis.clauses)}

## Risk Assessments ({len(analysis.risks)})
{chr(10).join(f"- [{r.risk_level.value.upper()}] Clause {r.clause_id}: {r.explanation[:100]}..." for r in analysis.risks)}

## Recommendations ({len(analysis.recommendations)})
{chr(10).join(f"- [Priority {r.priority}] {r.action}" for r in analysis.recommendations)}
"""
                )
            ],
        )

        await task_manager.add_artifact(task_id, artifact)

        # Complete the task
        await task_manager.complete_task(
            task_id,
            Message(
                role="agent",
                parts=[TextPart(text=analysis.summary)],
            ),
        )

        logger.info(
            "Task completed",
            task_id=task_id,
            clauses=len(analysis.clauses),
            risks=len(analysis.risks),
            recommendations=len(analysis.recommendations),
        )

    except Exception as e:
        logger.exception("Task processing failed", task_id=task_id)
        await task_manager.fail_task(task_id, str(e))


# Method handlers
METHOD_HANDLERS = {
    "tasks/send": handle_tasks_send,
    "tasks/get": handle_tasks_get,
    "tasks/cancel": handle_tasks_cancel,
}


@router.post("/a2a")
@limiter.limit(lambda: f"{get_settings().rate_limit_per_minute}/minute")
async def handle_jsonrpc(
    request: Request,
    background_tasks: BackgroundTasks,
    api_key: ApiKeyDep,
) -> dict:
    """Handle A2A JSON-RPC requests.

    This is the main endpoint for A2A protocol communication.
    Requires X-API-Key header if API_KEY is configured in settings.
    """
    try:
        body = await request.json()
    except Exception:
        return make_error_response(
            "null",
            PARSE_ERROR,
            "Parse error: Invalid JSON",
        ).model_dump(exclude_none=True)

    # Validate JSON-RPC request
    try:
        rpc_request = JsonRpcRequest(**body)
    except ValidationError as e:
        return make_error_response(
            body.get("id", "null"),
            INVALID_REQUEST,
            f"Invalid Request: {e}",
        ).model_dump(exclude_none=True)

    logger.info(
        "A2A request received",
        method=rpc_request.method,
        request_id=rpc_request.id,
    )

    # Check if method exists
    handler = METHOD_HANDLERS.get(rpc_request.method)
    if not handler:
        return make_error_response(
            rpc_request.id,
            METHOD_NOT_FOUND,
            f"Method not found: {rpc_request.method}",
        ).model_dump(exclude_none=True)

    # Execute method
    try:
        if rpc_request.method == "tasks/send":
            result = await handler(rpc_request.params, background_tasks)
        else:
            result = await handler(rpc_request.params)

        return make_success_response(
            rpc_request.id,
            result,
        ).model_dump(exclude_none=True)

    except TaskNotFoundError as e:
        return make_error_response(
            rpc_request.id,
            TASK_NOT_FOUND,
            str(e),
        ).model_dump(exclude_none=True)

    except InvalidStateTransitionError as e:
        return make_error_response(
            rpc_request.id,
            INVALID_STATE,
            str(e),
        ).model_dump(exclude_none=True)

    except ValueError as e:
        return make_error_response(
            rpc_request.id,
            INVALID_PARAMS,
            str(e),
        ).model_dump(exclude_none=True)

    except Exception as e:
        logger.exception("Internal error processing request")
        return make_error_response(
            rpc_request.id,
            INTERNAL_ERROR,
            f"Internal error: {e}",
        ).model_dump(exclude_none=True)
