"""A2A Protocol Pydantic models.

Based on the A2A specification: https://google.github.io/A2A/specification/
"""

from datetime import datetime
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field


# =============================================================================
# Agent Card Models
# =============================================================================


class AgentSkill(BaseModel):
    """A skill that the agent can perform."""

    id: str
    name: str
    description: str
    tags: list[str] = Field(default_factory=list)
    examples: list[str] = Field(default_factory=list)


class AgentCapabilities(BaseModel):
    """Agent capability flags."""

    streaming: bool = True
    push_notifications: bool = Field(default=False, alias="pushNotifications")
    state_transition_history: bool = Field(default=False, alias="stateTransitionHistory")


class AgentCard(BaseModel):
    """A2A Agent Card - describes agent capabilities."""

    name: str
    description: str
    url: str
    version: str
    capabilities: AgentCapabilities = Field(default_factory=AgentCapabilities)
    skills: list[AgentSkill] = Field(default_factory=list)
    default_input_modes: list[str] = Field(
        default=["text"], alias="defaultInputModes"
    )
    default_output_modes: list[str] = Field(
        default=["text"], alias="defaultOutputModes"
    )
    documentation_url: str | None = Field(default=None, alias="documentationUrl")
    provider: dict[str, str] | None = None

    class Config:
        populate_by_name = True


# =============================================================================
# Task Models
# =============================================================================


class TaskState(str, Enum):
    """Possible states for a task."""

    SUBMITTED = "submitted"
    WORKING = "working"
    INPUT_REQUIRED = "input-required"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELED = "canceled"


class TextPart(BaseModel):
    """Text content part."""

    type: Literal["text"] = "text"
    text: str


class FilePart(BaseModel):
    """File content part."""

    type: Literal["file"] = "file"
    file: dict[str, Any]  # Contains uri, mimeType, name, etc.


class DataPart(BaseModel):
    """Structured data part."""

    type: Literal["data"] = "data"
    data: dict[str, Any]


Part = TextPart | FilePart | DataPart


class Message(BaseModel):
    """A message in the task conversation."""

    role: Literal["user", "agent"]
    parts: list[Part]
    metadata: dict[str, Any] = Field(default_factory=dict)


class TaskStatus(BaseModel):
    """Current status of a task."""

    state: TaskState
    message: Message | None = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class Artifact(BaseModel):
    """An output artifact from a task."""

    name: str
    description: str | None = None
    parts: list[Part]
    index: int = 0
    metadata: dict[str, Any] = Field(default_factory=dict)


class Task(BaseModel):
    """A2A Task representation."""

    id: str
    status: TaskStatus
    artifacts: list[Artifact] = Field(default_factory=list)
    history: list[Message] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


# =============================================================================
# JSON-RPC Models
# =============================================================================


class JsonRpcRequest(BaseModel):
    """JSON-RPC 2.0 request."""

    jsonrpc: Literal["2.0"] = "2.0"
    method: str
    id: str | int
    params: dict[str, Any] = Field(default_factory=dict)


class JsonRpcError(BaseModel):
    """JSON-RPC 2.0 error object."""

    code: int
    message: str
    data: Any | None = None


class JsonRpcResponse(BaseModel):
    """JSON-RPC 2.0 response."""

    jsonrpc: Literal["2.0"] = "2.0"
    id: str | int
    result: Any | None = None
    error: JsonRpcError | None = None


# =============================================================================
# Task Request/Response Models
# =============================================================================


class TaskSendParams(BaseModel):
    """Parameters for tasks/send method."""

    id: str
    message: Message
    metadata: dict[str, Any] = Field(default_factory=dict)


class TaskGetParams(BaseModel):
    """Parameters for tasks/get method."""

    id: str
    history_length: int | None = Field(default=None, alias="historyLength")


class TaskCancelParams(BaseModel):
    """Parameters for tasks/cancel method."""

    id: str


class TaskResult(BaseModel):
    """Result of a task operation."""

    id: str
    status: TaskStatus
    artifacts: list[Artifact] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
