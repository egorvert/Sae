"""Contract Review Agent - LangGraph workflow for contract analysis.

This agent orchestrates the contract review process:
1. Extract clauses from the contract
2. Analyze each clause for risks
3. Generate recommendations for improvements
"""

import structlog
from langgraph.graph import END, StateGraph

from sae.agents.nodes.analyze_risks import analyze_risks
from sae.agents.nodes.extract_clauses import extract_clauses
from sae.agents.nodes.generate_recommendations import generate_recommendations
from sae.agents.state import ContractInput, ContractOutput, ContractReviewState
from sae.models.clauses import ContractAnalysis, RiskLevel

logger = structlog.get_logger()


def should_continue(state: ContractReviewState) -> str:
    """Determine the next step based on current status.

    Args:
        state: Current agent state

    Returns:
        Next node name or END
    """
    status = state.get("status", "pending")

    if status == "failed":
        return "end"
    elif status == "extracting":
        return "extract"
    elif status == "analyzing":
        return "analyze"
    elif status == "recommending":
        return "recommend"
    elif status == "complete":
        return "end"
    else:
        return "extract"


def create_contract_review_graph() -> StateGraph:
    """Create the contract review workflow graph.

    Returns:
        Compiled LangGraph StateGraph
    """
    # Create the graph
    workflow = StateGraph(ContractReviewState)

    # Add nodes
    workflow.add_node("extract", extract_clauses)
    workflow.add_node("analyze", analyze_risks)
    workflow.add_node("recommend", generate_recommendations)

    # Define edges
    workflow.set_entry_point("extract")

    # Conditional routing based on status
    workflow.add_conditional_edges(
        "extract",
        should_continue,
        {
            "analyze": "analyze",
            "end": END,
        },
    )

    workflow.add_conditional_edges(
        "analyze",
        should_continue,
        {
            "recommend": "recommend",
            "end": END,
        },
    )

    workflow.add_conditional_edges(
        "recommend",
        should_continue,
        {
            "end": END,
        },
    )

    return workflow.compile()


# Create a single instance of the compiled graph
contract_review_graph = create_contract_review_graph()


async def run_contract_review(input_data: ContractInput) -> ContractOutput:
    """Run the contract review workflow.

    Args:
        input_data: Contract input with text and metadata

    Returns:
        Contract review output with analysis results
    """
    logger.info(
        "Starting contract review",
        task_id=input_data.task_id,
        text_length=len(input_data.contract_text),
    )

    # Initialize state
    initial_state: ContractReviewState = {
        "task_id": input_data.task_id,
        "contract_text": input_data.contract_text,
        "contract_metadata": input_data.metadata,
        "status": "extracting",
        "error": None,
        "clauses": [],
        "risks": [],
        "recommendations": [],
        "messages": [],
    }

    try:
        # Run the graph
        final_state = await contract_review_graph.ainvoke(initial_state)

        # Check for errors
        if final_state.get("status") == "failed":
            return ContractOutput(
                task_id=input_data.task_id,
                analysis=ContractAnalysis(
                    contract_id=input_data.task_id,
                    summary=f"Analysis failed: {final_state.get('error', 'Unknown error')}",
                    overall_risk=RiskLevel.HIGH,
                ),
                success=False,
                error=final_state.get("error"),
            )

        # Build the analysis result
        clauses = final_state.get("clauses", [])
        risks = final_state.get("risks", [])
        recommendations = final_state.get("recommendations", [])

        # Determine overall risk level
        if any(r.risk_level == RiskLevel.CRITICAL for r in risks):
            overall_risk = RiskLevel.CRITICAL
        elif any(r.risk_level == RiskLevel.HIGH for r in risks):
            overall_risk = RiskLevel.HIGH
        elif any(r.risk_level == RiskLevel.MEDIUM for r in risks):
            overall_risk = RiskLevel.MEDIUM
        else:
            overall_risk = RiskLevel.LOW

        # Build summary
        summary_parts = [
            f"Analyzed contract with {len(clauses)} clauses.",
            f"Found {len(risks)} potential issues.",
        ]

        critical_count = sum(1 for r in risks if r.risk_level == RiskLevel.CRITICAL)
        high_count = sum(1 for r in risks if r.risk_level == RiskLevel.HIGH)

        if critical_count > 0:
            summary_parts.append(f"{critical_count} critical risks require immediate attention.")
        if high_count > 0:
            summary_parts.append(f"{high_count} high-priority issues should be addressed.")

        summary_parts.append(f"Generated {len(recommendations)} recommendations for improvement.")

        analysis = ContractAnalysis(
            contract_id=input_data.task_id,
            summary=" ".join(summary_parts),
            clauses=clauses,
            risks=risks,
            recommendations=recommendations,
            missing_clauses=[],  # TODO: Implement missing clause detection
            overall_risk=overall_risk,
            metadata=input_data.metadata,
        )

        logger.info(
            "Contract review complete",
            task_id=input_data.task_id,
            clause_count=len(clauses),
            risk_count=len(risks),
            recommendation_count=len(recommendations),
            overall_risk=overall_risk.value,
        )

        return ContractOutput(
            task_id=input_data.task_id,
            analysis=analysis,
            success=True,
        )

    except Exception as e:
        logger.exception("Contract review failed", task_id=input_data.task_id)
        return ContractOutput(
            task_id=input_data.task_id,
            analysis=ContractAnalysis(
                contract_id=input_data.task_id,
                summary=f"Analysis failed due to an unexpected error: {e}",
                overall_risk=RiskLevel.HIGH,
            ),
            success=False,
            error=str(e),
        )
