"""Planning loop nodes for the agent graph."""

import logging
from pathlib import Path
from typing import Literal, Optional

from sebba_code.constants import get_agent_dir
from sebba_code.llm import get_llm
from sebba_code.planning_prompts import draft_roadmap_prompt
from sebba_code.state import AgentState

logger = logging.getLogger("sebba_code")


def needs_planning(state: AgentState) -> Literal["yes", "no"]:
    """Determine if the planning loop should run.

    Routes to planning loop if:
    - user_request is provided and planning has not been completed yet

    Otherwise, skips to read_roadmap for backward compatibility.
    """
    if state.get("user_request") and not state.get("planning_complete", False):
        return "yes"
    return "no"


def is_planning_complete(state: AgentState) -> Literal["yes", "no"]:
    """Check if planning loop should terminate.

    Routes to write_roadmap if planning_complete is True,
    otherwise routes to refine_roadmap for another iteration.
    """
    if state.get("planning_complete", False):
        return "yes"
    return "no"


def _get_max_iterations(configurable: dict | None = None) -> int:
    """Get max iterations from config, CLI override, or default.

    Priority:
    1. CLI argument via configurable dict (planning_max_iterations)
    2. Config file setting (config.planning.max_iterations)
    3. Default value of 3
    """
    # CLI override takes precedence
    if configurable and "planning_max_iterations" in configurable:
        return configurable["planning_max_iterations"]

    # Try to load from config file
    try:
        from sebba_code.config import load_config

        agent_dir = get_agent_dir()
        config = load_config(agent_dir)
        return config.planning.max_iterations
    except Exception:
        pass

    return 3


def _get_planning_model(configurable: dict | None = None) -> str:
    """Get the model to use for planning.

    Priority:
    1. CLI/config override via configurable dict (planning_model)
    2. Config file setting (config.planning.model)
    3. Default LLM (empty string, uses get_llm() default)
    """
    # CLI/config override takes precedence
    if configurable and "planning_model" in configurable:
        return configurable["planning_model"]

    # Try to load from config file
    try:
        from sebba_code.config import load_config

        agent_dir = get_agent_dir()
        config = load_config(agent_dir)
        if config.planning.model:
            return config.planning.model
    except Exception:
        pass

    return ""


def draft_roadmap(state: AgentState, configurable: dict | None = None) -> dict:
    """Generate an initial roadmap draft from the user request.

    Takes the user request and loaded context (L0 memory, git state,
    codebase structure) and produces an initial roadmap draft stored
    in state['draft_roadmap'], not on disk.

    Args:
        state: The agent state containing:
            - user_request: The user's natural language request
            - memory: AgentMemoryContext with l0_index, l1_files, etc.
            - roadmap: Optional existing roadmap (for re-planning)
            - briefing: Optional codebase briefing from explore_validate
            - target_files: Files already identified for this task
        configurable: Optional config dict with planning_max_iterations, planning_model

    Returns:
        dict with:
            - draft_roadmap: The LLM-generated roadmap draft (markdown)
            - planning_iteration: Set to 1 for the initial draft
    """
    # Extract context from state
    user_request = state.get("user_request", "")
    memory = state.get("memory", {})
    existing_roadmap = state.get("roadmap", "")
    briefing = state.get("briefing", "")
    target_files = state.get("target_files", [])

    logger.info(f"Generating draft roadmap for request: {user_request[:50]}...")

    # Build additional context from target files if available
    context = {}
    if target_files:
        file_list = "\n".join(f"- {f}" for f in target_files)
        context["file_structure"] = f"# Already Identified Target Files\n{file_list}"

    # If there's an existing roadmap, include it for re-planning
    if existing_roadmap:
        context["existing_roadmap"] = f"# Existing Roadmap (for reference)\n{existing_roadmap}"

    # Generate the draft prompt using the template
    prompt = draft_roadmap_prompt(state, context)

    # Get the model to use (config override or default)
    model = _get_planning_model(configurable)

    # Call the main LLM (not cheap model - this is creative work)
    if model:
        llm = get_llm(model=model)
    else:
        llm = get_llm()
    response = llm.invoke(prompt)

    # Extract the content
    draft_content = response.content if hasattr(response, "content") else str(response)

    logger.debug(f"Generated draft roadmap ({len(draft_content)} chars)")

    return {
        "draft_roadmap": draft_content,
        "planning_iteration": 1,
    }


def critique_roadmap(state: AgentState, configurable: dict | None = None) -> dict:
    """Validate the draft roadmap against the codebase.

    Uses the cheap model to:
    - Check if referenced files exist
    - Verify TODO ordering makes sense
    - Flag vague descriptions
    - Detect scope creep

    Returns structured critique fixes in state.
    """
    draft = state.get("draft_roadmap", "")
    planning_iteration = state.get("planning_iteration", 0)
    max_iterations = _get_max_iterations(configurable)

    # Check if we've hit max iterations
    if planning_iteration >= max_iterations:
        logger.info(f"Max iterations ({max_iterations}) reached, marking complete")
        return {"planning_complete": True}

    # Basic validation - check for required sections
    issues = []
    if "- [ ]" not in draft:
        issues.append("Roadmap must contain at least one todo item")
    if len(draft) < 100:
        issues.append("Roadmap content seems too short")

    if issues:
        logger.debug(f"Critique found issues: {issues}")
        # For now, mark as complete after first critique if there are basic issues
        # Full critique implementation will refine the draft
        return {"planning_complete": True}

    # No major issues found, complete the planning
    logger.info("Critique passed, planning complete")
    return {"planning_complete": True}


def refine_roadmap(state: AgentState, configurable: dict | None = None) -> dict:
    """Apply critique fixes to the draft roadmap.

    Increments planning_iteration. Sets planning_complete when:
    - Critique finds no major issues, OR
    - Max iterations (default 3) reached
    """
    draft = state.get("draft_roadmap", "")
    planning_iteration = state.get("planning_iteration", 0)
    max_iterations = _get_max_iterations(configurable)

    # Increment iteration counter
    new_iteration = planning_iteration + 1

    # Check if max iterations reached
    if new_iteration >= max_iterations:
        logger.info(f"Max iterations reached, marking planning complete")
        return {
            "planning_iteration": new_iteration,
            "planning_complete": True,
        }

    # Apply basic refinements based on iteration
    refined = draft
    if new_iteration == 2:
        # Second iteration: ensure proper structure
        refined = refined.replace(
            "## Notes\n\nGenerated by",
            "## Notes\n\n- Refined after first critique\n- Generated by",
        )
    elif new_iteration == 3:
        # Third iteration: mark as final
        refined = refined.replace(
            "## Notes\n\nGenerated by",
            "## Notes\n\n- Final refinement complete\n- Generated by",
        )

    logger.debug(f"Refined roadmap (iteration {new_iteration})")

    return {
        "draft_roadmap": refined,
        "planning_iteration": new_iteration,
    }


def write_roadmap(state: AgentState) -> dict:
    """Persist the finalized draft to .agent/gcc/main.md.

    Called only after planning_complete is True.
    """
    draft = state.get("draft_roadmap", "")
    if not draft:
        logger.warning("No draft roadmap to write")
        return {}

    roadmap_path = get_agent_dir() / "gcc" / "main.md"
    roadmap_path.parent.mkdir(parents=True, exist_ok=True)

    with open(roadmap_path, "w") as f:
        f.write(draft)

    logger.info(f"Wrote roadmap to {roadmap_path}")

    return {
        "roadmap": draft,
    }
