"""Session-level extraction — writes session summary and applies collected memory updates."""

import logging
from datetime import date

from sebba_code.constants import DEBUG_PROMPTS, get_agent_dir
from sebba_code.helpers.memory_ops import (
    append_or_create,
    apply_index_updates,
    apply_memory_updates,
    apply_new_rules,
)
from sebba_code.state import AgentState

logger = logging.getLogger("sebba_code")


def extract_session(state: AgentState) -> dict:
    """Apply collected memory updates and write session summary."""
    logger.info("Extracting session into lasting memory")
    agent_dir = get_agent_dir()
    results = state.get("task_results", [])
    completed = state.get("tasks_completed_this_session", [])

    if not results and not completed:
        return {}

    # Apply memory updates collected from each worker
    for result in results:
        updates = result.get("memory_updates", {})
        if updates:
            try:
                apply_memory_updates(updates.get("memory_updates", []))
                apply_index_updates(updates.get("index_updates", []))
                apply_new_rules(updates.get("new_rules", []))
            except Exception:
                logger.warning("Failed to apply memory updates from task %s",
                               result.get("task_id"), exc_info=True)

    # Write session summary
    parts = []
    for result in results:
        part = f"## Task: {result.get('task_id', 'unknown')}\n"
        part += f"**Summary:** {result.get('summary', 'no summary')}\n\n"
        part += f"### What was done\n{result.get('what_i_did', 'unknown')}\n"
        if result.get("decisions_made"):
            part += f"\n### Decisions Made\n{result['decisions_made']}\n"
        if result.get("files_touched"):
            part += f"\n### Files Touched\n{result['files_touched']}\n"
        parts.append(part)

    if parts:
        session_content = f"# Session {date.today().isoformat()}\n\n"
        session_content += f"Tasks completed: {len(results)}\n\n"
        session_content += "\n\n---\n\n".join(parts)

        session_file = agent_dir / "sessions" / f"{date.today().isoformat()}.md"
        append_or_create(session_file, session_content)

    return {}
