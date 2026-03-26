"""Human-in-the-loop approval and DAG construction nodes."""

import logging
from typing import Literal

from langgraph.types import Command, interrupt

from sebba_code.helpers.parsing import parse_json
from sebba_code.state import AgentState, Task

logger = logging.getLogger("sebba_code")


def build_dag(state: AgentState) -> dict:
    """Parse draft_plan JSON into the tasks dict with proper initialization."""
    draft = state.get("draft_plan", "")
    if not draft:
        logger.warning("No draft plan to build DAG from")
        return {"tasks": {}}

    parsed = parse_json(draft)
    task_list = parsed.get("tasks", [])

    tasks: dict[str, Task] = {}
    for t in task_list:
        task_id = t["id"]
        tasks[task_id] = Task(
            id=task_id,
            description=t["description"],
            status="pending",
            depends_on=t.get("depends_on", []),
            blocked_reason="",
            result_summary="",
            files_touched=[],
            target_files=t.get("target_files", []),
            progress_summary="",
        )

    logger.info("Built DAG with %d tasks", len(tasks))
    return {"tasks": tasks}


def _format_plan_for_display(tasks: dict[str, Task]) -> str:
    """Format the task DAG for human review."""
    lines = ["# Execution Plan\n"]
    for tid, task in tasks.items():
        deps = ", ".join(task["depends_on"]) if task["depends_on"] else "none"
        files = ", ".join(task["target_files"]) if task["target_files"] else "none"
        lines.append(f"## {tid}: {task['description']}")
        lines.append(f"  Dependencies: {deps}")
        lines.append(f"  Target files: {files}")
        lines.append("")
    return "\n".join(lines)


def human_approval(state: AgentState) -> Command[Literal["dispatch_tasks", "plan_draft"]]:
    """Pause for human approval of the plan.

    Uses interrupt() to present the plan. The user resumes with:
    - True / "yes" / "approve" → proceed to execution
    - Any other string → rejection reason, loops back to planning
    """
    tasks = state.get("tasks", {})
    plan_display = _format_plan_for_display(tasks)

    response = interrupt({
        "type": "plan_approval",
        "plan": plan_display,
        "task_count": len(tasks),
        "question": "Approve this plan? Reply 'yes' or provide feedback to revise.",
    })

    if response is True or (isinstance(response, str) and response.lower().strip() in ("yes", "approve", "y", "ok")):
        logger.info("Plan approved by user")
        return Command(goto="dispatch_tasks", update={"plan_approved": True})

    reason = response if isinstance(response, str) else "Rejected without reason"
    logger.info("Plan rejected: %s", reason)
    return Command(
        goto="plan_draft",
        update={
            "plan_approved": False,
            "rejection_reason": reason,
            "planning_complete": False,
            "planning_iteration": 0,
        },
    )
