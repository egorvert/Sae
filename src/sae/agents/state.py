"""Agent state definitions for the contract review workflow."""

from typing import Annotated, Literal

from langgraph.graph.message import add_messages
from pydantic import BaseModel, Field
from typing_extensions import TypedDict

from sae.models.clauses import (
    ContractAnalysis,
    ExtractedClause,
    Recommendation,
    RiskAssessment,
)


class ContractReviewState(TypedDict):
    """State for the contract review agent.

    This state is passed between nodes in the LangGraph workflow.
    """

    # Input
    task_id: str
    contract_text: str
    contract_metadata: dict

    # Processing state
    status: Literal["pending", "extracting", "analyzing", "recommending", "complete", "failed"]
    error: str | None

    # Extracted data
    clauses: list[ExtractedClause]
    risks: list[RiskAssessment]
    recommendations: list[Recommendation]

    # Messages for LLM context
    messages: Annotated[list, add_messages]


class ContractInput(BaseModel):
    """Input for contract review."""

    task_id: str = Field(description="Task ID for tracking")
    contract_text: str = Field(description="Full text of the contract to review")
    metadata: dict = Field(
        default_factory=dict,
        description="Additional metadata about the contract",
    )


class ContractOutput(BaseModel):
    """Output from contract review."""

    task_id: str
    analysis: ContractAnalysis
    success: bool = True
    error: str | None = None
