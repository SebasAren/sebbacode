"""Defines the LangGraph StateGraph for the planning-only workflow."""

from langgraph.graph import END, START, StateGraph

from sebba_code.nodes.planning import (
    critique_roadmap,
    draft_roadmap,
    is_planning_complete,
    refine_roadmap,
    write_roadmap,
)
from sebba_code.state import PlanState


def build_plan_graph():
    """Build and compile the planning-only graph.

    Flow: draft → critique → [complete?] → write | refine → critique (loop)
    """
    graph = StateGraph(PlanState)

    graph.add_node("draft_roadmap", draft_roadmap)
    graph.add_node("critique_roadmap", critique_roadmap)
    graph.add_node("refine_roadmap", refine_roadmap)
    graph.add_node("write_roadmap", write_roadmap)

    graph.add_edge(START, "draft_roadmap")
    graph.add_edge("draft_roadmap", "critique_roadmap")

    graph.add_conditional_edges(
        "critique_roadmap",
        is_planning_complete,
        {"yes": "write_roadmap", "no": "refine_roadmap"},
    )
    graph.add_edge("refine_roadmap", "critique_roadmap")
    graph.add_edge("write_roadmap", END)

    return graph.compile()
