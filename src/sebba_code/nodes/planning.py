"""Planning loop nodes for the agent graph."""

import logging
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Literal

from langchain_core.messages import HumanMessage, ToolMessage

from sebba_code.constants import get_agent_dir
from sebba_code.helpers.parsing import parse_json
from sebba_code.llm import get_llm
from sebba_code.planning_prompts import draft_plan_prompt
from sebba_code.state import AgentState

logger = logging.getLogger("sebba_code")

# Patterns that indicate an explore/investigation task
# These tasks should typically be done by the planner directly,
# not delegated to subagents
EXPLORE_PATTERNS = [
    r"\bexplore\b",
    r"\binvestigate\b",
    r"\bfind\s+(where|what|how|which|whether)\b",
    r"\bdiscover\b",
    r"\bunderstand\b",
    r"\banalyze\s+(codebase|existing|structure|patterns)\b",
    r"\bcheck\s+(existing|where|how)\b",
    r"\blook\s+(at|into)\b",
    r"\bexamine\b",
    r"\blocate\b",
    r"\bidentify\s+(where|what|which)\b",
    r"\bsee\s+(how|what|where)\b",
    r"\bexplore\s+(how|what|where)\b",
]


def is_planning_complete(state: AgentState) -> Literal["yes", "no"]:
    """Check if planning loop should terminate."""
    if state.get("planning_complete", False):
        return "yes"
    return "no"


def _get_max_iterations(configurable: dict | None = None) -> int:
    """Get max iterations from config, CLI override, or default."""
    if configurable and "planning_max_iterations" in configurable:
        return configurable["planning_max_iterations"]
    try:
        from sebba_code.config import load_config
        agent_dir = get_agent_dir()
        config = load_config(agent_dir)
        return config.planning.max_iterations
    except Exception:
        pass
    return 3


def _get_planning_model(configurable: dict | None = None) -> str:
    """Get the model to use for planning."""
    if configurable and "planning_model" in configurable:
        return configurable["planning_model"]
    try:
        from sebba_code.config import load_config
        agent_dir = get_agent_dir()
        config = load_config(agent_dir)
        if config.planning.model:
            return config.planning.model
    except Exception:
        pass
    return ""


MAX_TOOL_ROUNDS = 3


def _run_tool_calls_parallel(tool_calls, explore_tool):
    """Execute multiple explore_codebase calls in parallel, return ToolMessages."""
    results = {}
    with ThreadPoolExecutor() as pool:
        futures = {
            pool.submit(explore_tool.invoke, tc["args"]): tc
            for tc in tool_calls
        }
        for future in as_completed(futures):
            tc = futures[future]
            try:
                result = future.result()
            except Exception as e:
                result = f"Error: {e}"
            results[tc["id"]] = result

    # Return ToolMessages in original order
    return [
        ToolMessage(content=results[tc["id"]], tool_call_id=tc["id"])
        for tc in tool_calls
    ]


def plan_draft(state: AgentState, configurable: dict | None = None) -> dict:
    """Generate a structured task plan with dependencies as JSON.

    Uses a tool-calling loop with explore_codebase so the planner can
    explore the codebase before creating tasks. On rejection, includes
    the rejected plan and reason for context.
    """
    from sebba_code.tools.explore_agent import explore_codebase

    user_request = state.get("user_request", "")
    rejection_reason = state.get("rejection_reason", "")
    previous_plan = state.get("draft_plan", "")

    logger.info("Generating task plan for: %s", user_request[:50])

    context = {}
    if rejection_reason and previous_plan:
        context["rejected_plan"] = previous_plan
        context["rejection_reason"] = rejection_reason

    prompt = draft_plan_prompt(state, context)

    model = _get_planning_model(configurable)
    llm = get_llm(model=model) if model else get_llm()
    llm_with_tools = llm.bind_tools([explore_codebase])

    messages = [HumanMessage(content=prompt)]

    for i in range(MAX_TOOL_ROUNDS):
        response = llm_with_tools.invoke(messages)
        messages.append(response)

        if not getattr(response, "tool_calls", None):
            break

        logger.info(
            "plan_draft: round %d — %d explore calls",
            i + 1,
            len(response.tool_calls),
        )
        tool_messages = _run_tool_calls_parallel(response.tool_calls, explore_codebase)
        messages.extend(tool_messages)

    draft_content = response.content if hasattr(response, "content") else str(response)
    logger.debug("Generated task plan (%d chars)", len(draft_content))

    current = state.get("planning_iteration", 0)
    return {
        "draft_plan": draft_content,
        "planning_iteration": max(current, 1),
    }


def _get_ancestors(task_id: str, tasks: list[dict]) -> set[str]:
    """Return the transitive set of ancestor task IDs (all dependencies, recursively)."""
    by_id = {t["id"]: t for t in tasks}
    ancestors: set[str] = set()
    stack = list(by_id.get(task_id, {}).get("depends_on", []))
    while stack:
        dep = stack.pop()
        if dep not in ancestors:
            ancestors.add(dep)
            stack.extend(by_id.get(dep, {}).get("depends_on", []))
    return ancestors


def _check_file_overlap(tasks: list[dict]) -> list[str]:
    """Check for target_files overlap between tasks that can run in parallel."""
    issues = []
    n = len(tasks)
    # Precompute ancestors for each task
    ancestor_map = {t["id"]: _get_ancestors(t["id"], tasks) for t in tasks}

    for i in range(n):
        for j in range(i + 1, n):
            t1, t2 = tasks[i], tasks[j]
            # Skip if one depends on the other (directly or transitively)
            if t1["id"] in ancestor_map.get(t2["id"], set()):
                continue
            if t2["id"] in ancestor_map.get(t1["id"], set()):
                continue
            # Check file overlap
            files1 = set(t1.get("target_files", []))
            files2 = set(t2.get("target_files", []))
            overlap = files1 & files2
            if overlap:
                issues.append(
                    f"Parallel tasks {t1['id']} and {t2['id']} both target "
                    f"{', '.join(sorted(overlap))} — add a dependency edge or split files"
                )
    return issues


def _is_explore_task(description: str) -> bool:
    """Check if a task description describes an explore/investigation task.

    Explore tasks should typically be done by the planner directly before
    creating subagent tasks, not delegated to subagents.
    """
    desc_lower = description.lower()
    for pattern in EXPLORE_PATTERNS:
        if re.search(pattern, desc_lower):
            return True
    return False


def _check_unnecessary_delegation(tasks: list[dict]) -> list[str]:
    """Identify explore tasks that were delegated to subagents but should have been done by the planner.

    Per the planning directive, the planner should run explore_codebase directly
    before creating subagent tasks. Tasks that are themselves explore/investigate
    tasks indicate the planner may have skipped this step.
    """
    flagged = []
    for task in tasks:
        description = task.get("description", "")
        if _is_explore_task(description):
            flagged.append(task["id"])
    return flagged


def plan_critique(state: AgentState, configurable: dict | None = None) -> dict:
    """Validate the draft plan structure, quality, and parallel-safety."""
    draft = state.get("draft_plan", "")
    planning_iteration = state.get("planning_iteration", 0)
    max_iterations = _get_max_iterations(configurable)

    if planning_iteration >= max_iterations:
        logger.info("Max iterations (%d) reached, marking complete", max_iterations)
        return {"planning_complete": True}

    # Basic structure validation
    issues = []
    if '"tasks"' not in draft and "'tasks'" not in draft:
        issues.append("Plan must contain a tasks array")
    if '"id"' not in draft:
        issues.append("Tasks must have IDs")
    if len(draft) < 50:
        issues.append("Plan content seems too short")

    # File overlap check for parallel tasks
    # Unnecessary delegation check for explore tasks
    if not issues:
        parsed = parse_json(draft)
        if parsed and "tasks" in parsed:
            overlap_issues = _check_file_overlap(parsed["tasks"])
            issues.extend(overlap_issues)

            # Check for explore tasks unnecessarily delegated to subagents
            delegation_flags = _check_unnecessary_delegation(parsed["tasks"])
            if delegation_flags:
                issues.append(
                    f"Explore tasks should be done by the planner directly "
                    f"(run explore_codebase before creating tasks): {', '.join(delegation_flags)}"
                )

    if issues:
        logger.debug("Critique found issues: %s", issues)
        # If we still have iterations left, reject so plan_refine can fix it
        if planning_iteration < max_iterations - 1:
            return {
                "planning_complete": False,
                "rejection_reason": "; ".join(issues),
                "planning_iteration": planning_iteration + 1,
            }
        # Out of iterations — accept with warning
        logger.warning("Critique issues remain but max iterations reached: %s", issues)
        return {"planning_complete": True}

    logger.info("Critique passed, planning complete")
    return {"planning_complete": True}


def plan_refine(state: AgentState, configurable: dict | None = None) -> dict:
    """Gate before re-drafting: stop if max iterations reached."""
    planning_iteration = state.get("planning_iteration", 0)
    max_iterations = _get_max_iterations(configurable)

    if planning_iteration >= max_iterations:
        logger.info("Max iterations reached, marking complete")
        return {"planning_complete": True}

    logger.debug("Routing to plan_draft for refinement (iteration %d)", planning_iteration)
    return {}
