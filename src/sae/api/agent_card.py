"""A2A Agent Card endpoint.

Serves the agent's capabilities at /.well-known/agent.json
"""

from fastapi import APIRouter, Request

from sae.config import get_settings
from sae.models.a2a import AgentCapabilities, AgentCard, AgentSkill

router = APIRouter()


def build_agent_card(base_url: str) -> AgentCard:
    """Build the Agent Card with current settings."""
    settings = get_settings()

    return AgentCard(
        name=settings.agent_name,
        description=settings.agent_description,
        url=base_url,
        version=settings.agent_version,
        capabilities=AgentCapabilities(
            streaming=True,
            push_notifications=False,
            state_transition_history=True,
        ),
        skills=[
            AgentSkill(
                id="contract_review",
                name="Contract Clause Review",
                description="Analyze contract documents to extract clauses, identify legal risks, and provide recommendations for improvement.",
                tags=["legal", "contracts", "compliance", "risk-analysis"],
                examples=[
                    "Review this NDA for potential risks",
                    "Extract all liability clauses from this agreement",
                    "Analyze the termination provisions in this contract",
                ],
            ),
        ],
        default_input_modes=["text", "file"],
        default_output_modes=["text"],
        provider={
            "name": "Sae",
            "url": "https://github.com/sae-legal",
        },
    )


@router.get("/.well-known/agent.json")
async def get_agent_card(request: Request) -> dict:
    """Serve the A2A Agent Card.

    This endpoint is the discovery mechanism for the A2A protocol.
    Other agents can fetch this to learn about our capabilities.
    """
    # Build base URL from request
    base_url = str(request.base_url).rstrip("/")

    agent_card = build_agent_card(base_url)
    return agent_card.model_dump(by_alias=True, exclude_none=True)
