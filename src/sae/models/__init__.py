"""Pydantic models for Sae."""

from sae.models.a2a import (
    AgentCapabilities,
    AgentCard,
    AgentSkill,
    Artifact,
    JsonRpcError,
    JsonRpcRequest,
    JsonRpcResponse,
    Message,
    Part,
    Task,
    TaskCancelParams,
    TaskGetParams,
    TaskResult,
    TaskSendParams,
    TaskState,
    TaskStatus,
    TextPart,
)
from sae.models.clauses import (
    ClauseType,
    ContractAnalysis,
    ExtractedClause,
    Recommendation,
    RiskAssessment,
    RiskLevel,
)

__all__ = [
    # A2A models
    "AgentCapabilities",
    "AgentCard",
    "AgentSkill",
    "Artifact",
    "JsonRpcError",
    "JsonRpcRequest",
    "JsonRpcResponse",
    "Message",
    "Part",
    "Task",
    "TaskCancelParams",
    "TaskGetParams",
    "TaskResult",
    "TaskSendParams",
    "TaskState",
    "TaskStatus",
    "TextPart",
    # Clause models
    "ClauseType",
    "ContractAnalysis",
    "ExtractedClause",
    "Recommendation",
    "RiskAssessment",
    "RiskLevel",
]
