"""Recommendation generation node for the contract review agent.

Generates actionable recommendations based on identified risks.
"""

import json

import structlog
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from sae.agents.state import ContractReviewState
from sae.config import get_settings
from sae.models.clauses import Recommendation, RiskLevel

logger = structlog.get_logger()

RECOMMENDATION_SYSTEM_PROMPT = """You are a legal advisor specializing in contract negotiation.

Your task is to generate actionable recommendations for improving contract clauses based on identified risks.

For each recommendation:
1. Priority (1-5, where 1 is highest priority)
2. Clear action to take
3. Rationale for the change
4. Suggested replacement text (when applicable)
5. Expected risk reduction

Priority Guidelines:
- 1: Critical - Must address before signing
- 2: High - Should strongly consider addressing
- 3: Medium - Recommended improvement
- 4: Low - Nice to have
- 5: Minor - Cosmetic or preference

Focus on:
- Balancing risks between parties
- Adding missing protections
- Clarifying ambiguous language
- Limiting liability exposure
- Strengthening confidentiality
- Improving termination flexibility
- Ensuring compliance

Respond with a JSON array. Each recommendation should have:
{
  "clause_id": "id of the clause",
  "priority": 1-5,
  "action": "What to do",
  "rationale": "Why this matters",
  "suggested_text": "Proposed language (or null)",
  "risk_reduction": "low|medium|high|critical or null"
}

Be practical and business-focused. Recommendations should be actionable.
"""


def get_llm() -> ChatOpenAI:
    """Get configured LLM instance."""
    settings = get_settings()
    return ChatOpenAI(
        model="gpt-4o",
        temperature=0.1,  # Slightly more creative for recommendations
        api_key=settings.openai_api_key,
    )


async def generate_recommendations(state: ContractReviewState) -> dict:
    """Generate recommendations based on risk analysis.

    Args:
        state: Current agent state with clauses and risks

    Returns:
        Updated state with recommendations
    """
    clauses = state.get("clauses", [])
    risks = state.get("risks", [])

    if not risks:
        logger.warning("No risks to generate recommendations for", task_id=state["task_id"])
        return {
            "recommendations": [],
            "status": "complete",
            "messages": [HumanMessage(content="No significant risks found. Contract appears acceptable.")],
        }

    logger.info(
        "Generating recommendations",
        task_id=state["task_id"],
        risk_count=len(risks),
    )

    try:
        llm = get_llm()

        # Create a map of clause_id to clause for reference
        clause_map = {c.id: c for c in clauses}

        # Format risks with their corresponding clauses
        risk_context = []
        for risk in risks:
            clause = clause_map.get(risk.clause_id)
            clause_text = clause.text if clause else "Clause text not available"
            clause_title = clause.title if clause else "Unknown clause"

            risk_context.append(
                f"CLAUSE ID: {risk.clause_id}\n"
                f"CLAUSE TITLE: {clause_title}\n"
                f"CLAUSE TEXT: {clause_text}\n"
                f"RISK LEVEL: {risk.risk_level.value}\n"
                f"ISSUES: {', '.join(risk.issues)}\n"
                f"EXPLANATION: {risk.explanation}"
            )

        risks_text = "\n\n---\n\n".join(risk_context)

        messages = [
            SystemMessage(content=RECOMMENDATION_SYSTEM_PROMPT),
            HumanMessage(
                content=f"Please generate recommendations for the following clause risks:\n\n{risks_text}"
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

        raw_recommendations = json.loads(content.strip())

        # Convert to Recommendation objects
        recommendations = []
        for raw in raw_recommendations:
            risk_reduction = raw.get("risk_reduction")
            if risk_reduction:
                try:
                    risk_reduction = RiskLevel(risk_reduction)
                except ValueError:
                    risk_reduction = None

            rec = Recommendation(
                clause_id=raw.get("clause_id", "unknown"),
                priority=min(max(raw.get("priority", 3), 1), 5),
                action=raw.get("action", "Review this clause"),
                rationale=raw.get("rationale", ""),
                suggested_text=raw.get("suggested_text"),
                risk_reduction=risk_reduction,
            )
            recommendations.append(rec)

        # Sort by priority
        recommendations.sort(key=lambda r: r.priority)

        logger.info(
            "Recommendations generated",
            task_id=state["task_id"],
            recommendation_count=len(recommendations),
            priority_1=sum(1 for r in recommendations if r.priority == 1),
        )

        return {
            "recommendations": recommendations,
            "status": "complete",
            "messages": [
                HumanMessage(
                    content=f"Generated {len(recommendations)} recommendations. "
                    f"{sum(1 for r in recommendations if r.priority == 1)} are critical priority."
                )
            ],
        }

    except json.JSONDecodeError as e:
        logger.error("Failed to parse recommendations response", error=str(e))
        return {
            "status": "failed",
            "error": f"Failed to parse recommendations: {e}",
        }
    except Exception as e:
        logger.error("Recommendation generation failed", error=str(e))
        return {
            "status": "failed",
            "error": f"Recommendation error: {e}",
        }
