"""API routes for Sae."""

from sae.api.agent_card import router as agent_card_router
from sae.api.jsonrpc import router as jsonrpc_router
from sae.api.streaming import router as streaming_router

__all__ = [
    "agent_card_router",
    "jsonrpc_router",
    "streaming_router",
]
