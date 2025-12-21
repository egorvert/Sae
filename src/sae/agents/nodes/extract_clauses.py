"""Clause extraction node for the contract review agent.

Uses OpenAI to intelligently extract and categorize clauses from contracts.
"""

import json
from uuid import uuid4

import structlog
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from sae.agents.state import ContractReviewState
from sae.config import get_settings
from sae.models.clauses import ClauseType, ExtractedClause

logger = structlog.get_logger()

EXTRACTION_SYSTEM_PROMPT = """You are a legal document analyst specializing in contract clause extraction.

Your task is to analyze the provided contract text and extract all significant clauses.

For each clause, identify:
1. The clause type (from the provided categories)
2. A clear title/heading
3. The exact text of the clause
4. Its location in the document (section number if available)

Clause types:
- indemnification: Clauses about compensation for losses
- liability: Limitation of liability, liability caps
- termination: How and when the contract can be ended
- confidentiality: NDA provisions, confidential information handling
- intellectual_property: IP ownership, licensing, work for hire
- payment: Payment terms, pricing, invoicing
- warranty: Warranties and guarantees
- force_majeure: Unforeseeable circumstances provisions
- dispute_resolution: How disputes are handled (arbitration, litigation)
- governing_law: Which jurisdiction's laws apply
- assignment: Whether the contract can be transferred
- amendment: How changes to the contract are made
- notice: How official notices must be delivered
- entire_agreement: Integration clauses
- severability: What happens if part of contract is invalid
- other: Any other significant provisions

Respond with a JSON array of clauses. Each clause should have:
{
  "type": "clause_type",
  "title": "Clause Title",
  "text": "Full clause text...",
  "location": "Section X.Y"
}

Extract ALL significant clauses. Be thorough but accurate.
"""


def get_llm() -> ChatOpenAI:
    """Get configured LLM instance."""
    settings = get_settings()
    return ChatOpenAI(
        model="gpt-4o",
        temperature=0,
        api_key=settings.openai_api_key,
    )


async def extract_clauses(state: ContractReviewState) -> dict:
    """Extract clauses from contract text.

    Args:
        state: Current agent state with contract_text

    Returns:
        Updated state with extracted clauses
    """
    logger.info(
        "Extracting clauses",
        task_id=state["task_id"],
        text_length=len(state["contract_text"]),
    )

    try:
        llm = get_llm()

        # Prepare messages
        messages = [
            SystemMessage(content=EXTRACTION_SYSTEM_PROMPT),
            HumanMessage(
                content=f"Please extract all clauses from the following contract:\n\n{state['contract_text']}"
            ),
        ]

        # Call LLM
        response = await llm.ainvoke(messages)
        content = response.content

        # Parse response
        # Handle case where response might be wrapped in markdown code blocks
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0]
        elif "```" in content:
            content = content.split("```")[1].split("```")[0]

        raw_clauses = json.loads(content.strip())

        # Convert to ExtractedClause objects
        clauses = []
        for i, raw in enumerate(raw_clauses):
            clause_type = raw.get("type", "other")
            try:
                clause_type_enum = ClauseType(clause_type)
            except ValueError:
                clause_type_enum = ClauseType.OTHER

            clause = ExtractedClause(
                id=str(uuid4())[:8],
                type=clause_type_enum,
                title=raw.get("title", f"Clause {i + 1}"),
                text=raw.get("text", ""),
                location=raw.get("location", f"Section {i + 1}"),
            )
            clauses.append(clause)

        logger.info(
            "Clauses extracted",
            task_id=state["task_id"],
            clause_count=len(clauses),
        )

        return {
            "clauses": clauses,
            "status": "analyzing",
            "messages": [
                HumanMessage(content=f"Extracted {len(clauses)} clauses from the contract.")
            ],
        }

    except json.JSONDecodeError as e:
        logger.error("Failed to parse clause extraction response", error=str(e))
        return {
            "status": "failed",
            "error": f"Failed to parse extracted clauses: {e}",
        }
    except Exception as e:
        logger.error("Clause extraction failed", error=str(e))
        return {
            "status": "failed",
            "error": f"Clause extraction error: {e}",
        }
