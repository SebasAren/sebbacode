"""Task management tools for the worker agent."""

from langchain_core.tools import tool


@tool
def mark_task_done(summary: str) -> str:
    """Signal that the current task is complete.

    Args:
        summary: Brief summary of what was accomplished
    """
    return f"Task marked complete: {summary}"


@tool
def signal_blocked(blocking_task_description: str, reason: str) -> str:
    """Signal that the current task is blocked and needs a prerequisite task created.

    This will create a new task in the DAG and make the current task depend on it.
    The current task will be re-queued after the blocking task completes.

    Args:
        blocking_task_description: Description of the prerequisite task that must be done first
        reason: Why the current task is blocked
    """
    return f"Blocked: {reason}. New prerequisite task will be created: {blocking_task_description}"


@tool
def add_subtask(description: str, target_files: str = "") -> str:
    """Add a new task to the execution DAG that was discovered during work.

    Use this when you find work that needs doing but is outside the scope of your current task.
    The new task will be added as an independent task (no dependencies by default).

    Args:
        description: Description of the new task
        target_files: Comma-separated list of target files (optional)
    """
    files = [f.strip() for f in target_files.split(",") if f.strip()] if target_files else []
    return f"Subtask added: {description}" + (f" (files: {', '.join(files)})" if files else "")
