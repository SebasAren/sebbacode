"""Defines the LangGraph StateGraph workflow for the coding agent."""

from langgraph.graph import END, START, StateGraph

from sebba_code.nodes.context import deepen_context
from sebba_code.nodes.done import roadmap_done
from sebba_code.nodes.execute import build_execute_subgraph
from sebba_code.nodes.explore import explore_bootstrap, explore_recon, explore_validate
from sebba_code.nodes.extract import extract_session, should_continue, sync_progress
from sebba_code.nodes.load_context import load_context, needs_bootstrap
from sebba_code.nodes.roadmap import has_todo, is_first_todo, read_roadmap
from sebba_code.nodes.rules import match_rules
from sebba_code.state import AgentState


def build_agent_graph():
    """Build and compile the full agent graph."""
    graph = StateGraph(AgentState)

    # Add nodes
    graph.add_node("load_context", load_context)
    graph.add_node("explore_bootstrap", explore_bootstrap)
    graph.add_node("read_roadmap", read_roadmap)
    graph.add_node("check_first_todo", lambda s: s)
    graph.add_node("explore_validate", explore_validate)
    graph.add_node("explore_recon", explore_recon)
    graph.add_node("match_rules", match_rules)
    graph.add_node("deepen_context", deepen_context)
    graph.add_node("execute_todo", build_execute_subgraph())
    graph.add_node("sync_progress", sync_progress)
    graph.add_node("extract_session", extract_session)
    graph.add_node("roadmap_done", roadmap_done)

    # Startup
    graph.add_edge(START, "load_context")
    graph.add_conditional_edges(
        "load_context",
        needs_bootstrap,
        {"yes": "explore_bootstrap", "no": "read_roadmap"},
    )
    graph.add_edge("explore_bootstrap", "read_roadmap")

    # Roadmap loop
    graph.add_conditional_edges(
        "read_roadmap",
        has_todo,
        {"yes": "check_first_todo", "no": "roadmap_done"},
    )
    graph.add_conditional_edges(
        "check_first_todo",
        is_first_todo,
        {"yes": "explore_validate", "no": "explore_recon"},
    )
    graph.add_edge("explore_validate", "explore_recon")

    # Context → execution
    graph.add_edge("explore_recon", "match_rules")
    graph.add_edge("match_rules", "deepen_context")
    graph.add_edge("deepen_context", "execute_todo")

    # Post-execution
    graph.add_edge("execute_todo", "sync_progress")
    graph.add_edge("sync_progress", "extract_session")
    graph.add_conditional_edges(
        "extract_session",
        should_continue,
        {"yes": "read_roadmap", "no": END},
    )
    graph.add_edge("roadmap_done", "extract_session")

    return graph.compile()
