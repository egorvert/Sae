"""Risk analysis node for the contract review agent.

Analyzes extracted clauses for legal risks and issues.
"""

import json

import structlog
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from sae.agents.state import ContractReviewState
from sae.config import get_settings
from sae.models.clauses import RiskAssessment, RiskLevel

logger = structlog.get_logger()

RISK_ANALYSIS_SYSTEM_PROMPT = """You are a legal risk analyst specializing in contract review.

Your task is to analyze contract clauses and identify potential legal risks.

For each clause, assess:
1. Risk level: low, medium, high, or critical
2. Confidence in your assessment (0.0 to 1.0)
3. Specific issues identified
4. Detailed explanation of the risk
5. Which party is most affected (client, vendor, both)

Risk Level Guidelines:
- low: Standard language, minimal concern
- medium: Some deviation from standard, worth noting
- high: Significant risk, should be addressed before signing
- critical: Major red flag, requires immediate attention

Look for issues such as:
- Unlimited liability exposure
- One-sided indemnification
- Weak confidentiality protections
- Unfavorable termination terms
- Missing standard protections
- Ambiguous language
- Unusual or aggressive terms
- IP rights concerns
- Payment risk
- Compliance gaps

Respond with a JSON array. Each risk assessment should have:
{
  "clause_id": "id of the clause",
  "risk_level": "low|medium|high|critical",
  "confidence": 0.85,
  "issues": ["Issue 1", "Issue 2"],
  "explanation": "Detailed explanation...",
  "affected_party": "client|vendor|both"
}

Be thorough but practical. Focus on real business and legal risks.
"""


def get_llm() -> ChatOpenAI:
    """Get configured LLM instance."""
    settings = get_settings()
    return ChatOpenAI(
        model="gpt-4o",
        temperature=0,
        api_key=settings.openai_api_key,
    )


async def analyze_risks(state: ContractReviewState) -> dict:
    """Analyze extracted clauses for risks.

    Args:
        state: Current agent state with extracted clauses

    Returns:
        Updated state with risk assessments
    """
    clauses = state.get("clauses", [])

    if not clauses:
        logger.warning("No clauses to analyze", task_id=state["task_id"])
        return {
            "risks": [],
            "status": "recommending",
            "messages": [HumanMessage(content="No clauses found to analyze.")],
        }

    logger.info(
        "Analyzing risks",
        task_id=state["task_id"],
        clause_count=len(clauses),
    )

    try:
        llm = get_llm()

        # Format clauses for analysis
        clauses_text = "\n\n".join(
            f"CLAUSE ID: {c.id}\nTYPE: {c.type.value}\nTITLE: {c.title}\nLOCATION: {c.location}\nTEXT:\n{c.text}"
            for c in clauses
        )

        messages = [
            SystemMessage(content=RISK_ANALYSIS_SYSTEM_PROMPT),
            HumanMessage(
                content=f"Please analyze the following contract clauses for risks:\n\n{clauses_text}"
            ),
        ]

        # Call LLM
        response = await llm.ainvoke(messages)
        content = response.content

        # Parse response
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0]
        elif "```" in content:
            content = content.split("```")[1].split("```")[0]

        raw_risks = json.loads(content.strip())

        # Convert to RiskAssessment objects
        risks = []
        for raw in raw_risks:
            risk_level = raw.get("risk_level", "low")
            try:
                risk_level_enum = RiskLevel(risk_level)
            except ValueError:
                risk_level_enum = RiskLevel.LOW

            risk = RiskAssessment(
                clause_id=raw.get("clause_id", "unknown"),
                risk_level=risk_level_enum,
                confidence=min(max(raw.get("confidence", 0.5), 0.0), 1.0),
                issues=raw.get("issues", []),
                explanation=raw.get("explanation", ""),
                affected_party=raw.get("affected_party", "both"),
            )
            risks.append(risk)

        # Count risk levels
        risk_counts = {
            "critical": sum(1 for r in risks if r.risk_level == RiskLevel.CRITICAL),
            "high": sum(1 for r in risks if r.risk_level == RiskLevel.HIGH),
            "medium": sum(1 for r in risks if r.risk_level == RiskLevel.MEDIUM),
            "low": sum(1 for r in risks if r.risk_level == RiskLevel.LOW),
        }

        logger.info(
            "Risk analysis complete",
            task_id=state["task_id"],
            risk_counts=risk_counts,
        )

        return {
            "risks": risks,
            "status": "recommending",
            "messages": [
                HumanMessage(
                    content=f"Analyzed {len(risks)} clauses. Found {risk_counts['critical']} critical, {risk_counts['high']} high, {risk_counts['medium']} medium risks."
                )
            ],
        }

    except json.JSONDecodeError as e:
        logger.error("Failed to parse risk analysis response", error=str(e))
        return {
            "status": "failed",
            "error": f"Failed to parse risk analysis: {e}",
        }
    except Exception as e:
        logger.error("Risk analysis failed", error=str(e))
        return {
            "status": "failed",
            "error": f"Risk analysis error: {e}",
        }
