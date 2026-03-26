"""Defines the unified LangGraph StateGraph for planning + DAG execution."""

from langgraph.graph import END, START, StateGraph

from sebba_code.nodes.approval import build_dag, human_approval
from sebba_code.nodes.dispatch import collect_results, dispatch_tasks
from sebba_code.nodes.explore import explore_bootstrap
from sebba_code.nodes.extract import extract_session
from sebba_code.nodes.load_context import load_context, needs_bootstrap
from sebba_code.nodes.plan_recon import plan_recon
from sebba_code.nodes.planning import (
    is_planning_complete,
    plan_critique,
    plan_draft,
    plan_refine,
)
from sebba_code.nodes.worker import build_task_worker
from sebba_code.state import AgentState


def build_agent_graph(checkpointer=None):
    """Build and compile the unified agent graph.

    Flow:
        START → load_context → [bootstrap?] → plan_draft → plan_critique
        → [complete?] → build_dag → human_approval → [approve?]
        → dispatch_tasks → task_worker(s) → collect_results → [more?]
        → extract_session → END
    """
    graph = StateGraph(AgentState)

    # --- Nodes ---
    graph.add_node("load_context", load_context)
    graph.add_node("explore_bootstrap", explore_bootstrap)
    graph.add_node("plan_recon", plan_recon)
    graph.add_node("plan_draft", plan_draft)
    graph.add_node("plan_critique", plan_critique)
    graph.add_node("plan_refine", plan_refine)
    graph.add_node("build_dag", build_dag)
    graph.add_node("human_approval", human_approval)
    graph.add_node("dispatch_tasks", dispatch_tasks)
    graph.add_node("task_worker", build_task_worker())
    graph.add_node("collect_results", collect_results)
    graph.add_node("extract_session", extract_session)

    # --- Edges ---

    # Entry
    graph.add_edge(START, "load_context")

    # Bootstrap check
    graph.add_conditional_edges(
        "load_context",
        needs_bootstrap,
        {"yes": "explore_bootstrap", "no": "plan_recon"},
    )
    graph.add_edge("explore_bootstrap", "plan_recon")
    graph.add_edge("plan_recon", "plan_draft")

    # Planning loop
    graph.add_edge("plan_draft", "plan_critique")
    graph.add_conditional_edges(
        "plan_critique",
        is_planning_complete,
        {"yes": "build_dag", "no": "plan_refine"},
    )
    graph.add_edge("plan_refine", "plan_critique")

    # DAG construction → approval
    graph.add_edge("build_dag", "human_approval")
    # human_approval returns Command routing to dispatch_tasks or plan_draft

    # Dispatch → workers → collect → loop or finish
    # dispatch_tasks returns Command with Send() to task_worker(s)
    # or Command(goto="extract_session") when done
    graph.add_edge("task_worker", "collect_results")
    # collect_results returns Command routing to dispatch_tasks or extract_session

    # Terminal
    graph.add_edge("extract_session", END)

    return graph.compile(checkpointer=checkpointer)
