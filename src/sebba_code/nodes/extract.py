"""Session-level extraction — writes session summary and emits L2 entries to state."""

import logging
import os
from datetime import date

from sebba_code.constants import get_agent_dir
from sebba_code.helpers.memory_ops import (
    append_or_create,
    apply_index_updates,
    apply_memory_updates,
    apply_new_rules,
)
from sebba_code.state import AgentState

logger = logging.getLogger("sebba_code")


def extract_session(state: AgentState) -> dict:
    """Apply collected memory updates and write session summary.

    L2 entries are stashed in state for the downstream ``summarize_to_l1``
    node to condense into L1.  The post-extraction hook is no longer used
    here — the synchronous summarisation step now lives in the graph.
    """
    logger.info("Extracting session into lasting memory")
    agent_dir = get_agent_dir()
    results = state.get("task_results", [])
    completed = state.get("tasks_completed_this_session", [])

    if not results and not completed:
        return {}

    # Collect L2 entries so the downstream node can summarise them
    l2_entries: list[dict] = []

    # Apply memory updates collected from each worker
    for result in results:
        updates = result.get("memory_updates", {})
        if updates:
            try:
                apply_memory_updates(updates.get("memory_updates", []))
                apply_index_updates(updates.get("index_updates", []))
                apply_new_rules(updates.get("new_rules", []))

                # Pull L2 content out of the memory_updates.  We look for
                # any entry that carries "content" — those are the detailed
                # L2 writes.
                for mu in updates.get("memory_updates", []):
                    if mu.get("content") and mu.get("action") in (
                        "create",
                        "append",
                    ):
                        l2_entries.append({
                            "content": mu["content"],
                            "file": mu.get("file", ""),
                            "topic": _topic_from_file(mu.get("file", "")),
                        })
            except Exception:
                logger.warning(
                    "Failed to apply memory updates from task %s",
                    result.get("task_id"), exc_info=True,
                )

    # Write session summary to .agent/sessions/
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

    # Pass L2 entries to the downstream summarisation node
    return {"l2_entries": l2_entries}


def _topic_from_file(file: str) -> str:
    """Derive a topic label from a memory file path.

    Uses the directory part as topic (consistent with memory_ops.py).
    E.g. ``"architecture/example.md"`` → ``"architecture"``.
    Falls back to the filename stem when there is no directory.
    """
    if not file:
        return "session"
    from pathlib import Path
    file_path = Path(file)
    if file_path.parent != Path("."):
        return str(file_path.parent)
    return file_path.stem or "session"
