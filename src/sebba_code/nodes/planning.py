"""Planning loop nodes for the agent graph."""

from typing import Literal

from sebba_code.state import AgentState


def needs_planning(state: AgentState) -> Literal["yes", "no"]:
    """Determine if the planning loop should run.

    Routes to planning loop if:
    - user_request is provided and planning has not been completed yet

    Otherwise, skips to read_roadmap for backward compatibility.
    """
    if state.get("user_request") and not state.get("planning_complete", False):
        return "yes"
    return "no"


def draft_roadmap(state: AgentState) -> AgentState:
    """Generate an initial roadmap draft from the user request.

    Takes the user request and loaded context (L0 memory, git state,
    codebase structure) and produces an initial roadmap draft stored
    in state['draft_roadmap'], not on disk.
    """
    # TODO: Implement with LLM call using loaded context
    raise NotImplementedError("draft_roadmap not yet implemented")


def critique_roadmap(state: AgentState) -> AgentState:
    """Validate the draft roadmap against the codebase.

    Uses the cheap model to:
    - Check if referenced files exist
    - Verify TODO ordering makes sense
    - Flag vague descriptions
    - Detect scope creep

    Returns structured critique fixes in state.
    """
    # TODO: Implement with get_cheap_llm()
    raise NotImplementedError("critique_roadmap not yet implemented")


def refine_roadmap(state: AgentState) -> AgentState:
    """Apply critique fixes to the draft roadmap.

    Increments planning_iteration. Sets planning_complete when:
    - Critique finds no major issues, OR
    - Max iterations (default 3) reached
    """
    # TODO: Implement with LLM call applying fixes
    raise NotImplementedError("refine_roadmap not yet implemented")


def write_roadmap(state: AgentState) -> AgentState:
    """Persist the finalized draft to .agent/gcc/main.md.

    Called only after planning_complete is True.
    """
    # TODO: Implement file writing to .agent/gcc/main.md
    raise NotImplementedError("write_roadmap not yet implemented")
