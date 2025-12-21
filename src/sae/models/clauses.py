"""Models for contract clause analysis."""

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class ClauseType(str, Enum):
    """Types of contract clauses."""

    INDEMNIFICATION = "indemnification"
    LIABILITY = "liability"
    TERMINATION = "termination"
    CONFIDENTIALITY = "confidentiality"
    INTELLECTUAL_PROPERTY = "intellectual_property"
    PAYMENT = "payment"
    WARRANTY = "warranty"
    FORCE_MAJEURE = "force_majeure"
    DISPUTE_RESOLUTION = "dispute_resolution"
    GOVERNING_LAW = "governing_law"
    ASSIGNMENT = "assignment"
    AMENDMENT = "amendment"
    NOTICE = "notice"
    ENTIRE_AGREEMENT = "entire_agreement"
    SEVERABILITY = "severability"
    OTHER = "other"


class RiskLevel(str, Enum):
    """Risk levels for clause analysis."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ExtractedClause(BaseModel):
    """A clause extracted from a contract."""

    id: str = Field(description="Unique identifier for the clause")
    type: ClauseType = Field(description="Type of clause")
    title: str = Field(description="Title or heading of the clause")
    text: str = Field(description="Full text of the clause")
    location: str = Field(description="Location in document (e.g., 'Section 5.2')")
    metadata: dict[str, Any] = Field(default_factory=dict)


class RiskAssessment(BaseModel):
    """Risk assessment for a specific clause."""

    clause_id: str = Field(description="ID of the assessed clause")
    risk_level: RiskLevel = Field(description="Overall risk level")
    confidence: float = Field(
        ge=0.0,
        le=1.0,
        description="Confidence score (0-1)",
    )
    issues: list[str] = Field(
        default_factory=list,
        description="List of identified issues",
    )
    explanation: str = Field(description="Detailed explanation of the risk")
    affected_party: str = Field(
        default="",
        description="Which party is affected (e.g., 'client', 'vendor', 'both')",
    )


class Recommendation(BaseModel):
    """A recommendation for improving a clause."""

    clause_id: str = Field(description="ID of the clause this recommendation is for")
    priority: int = Field(ge=1, le=5, description="Priority (1=highest, 5=lowest)")
    action: str = Field(description="Recommended action")
    rationale: str = Field(description="Why this change is recommended")
    suggested_text: str | None = Field(
        default=None,
        description="Suggested replacement text",
    )
    risk_reduction: RiskLevel | None = Field(
        default=None,
        description="Expected risk level after change",
    )


class ContractAnalysis(BaseModel):
    """Complete analysis of a contract."""

    contract_id: str
    summary: str = Field(description="Executive summary of the analysis")
    clauses: list[ExtractedClause] = Field(default_factory=list)
    risks: list[RiskAssessment] = Field(default_factory=list)
    recommendations: list[Recommendation] = Field(default_factory=list)
    missing_clauses: list[ClauseType] = Field(
        default_factory=list,
        description="Standard clauses that are missing",
    )
    overall_risk: RiskLevel = Field(description="Overall contract risk level")
    metadata: dict[str, Any] = Field(default_factory=dict)
