"""Implements the session extraction node for distilling commits into lasting memory."""

import logging
import re

from sebba_code.constants import DEBUG_PROMPTS, get_agent_dir
from sebba_code.helpers.memory_ops import (
    append_or_create,
    apply_index_updates,
    apply_memory_updates,
    apply_new_rules,
    format_session_from_commits,
)
from sebba_code.helpers.parsing import parse_json
from sebba_code.llm import get_llm
from sebba_code.state import AgentState


logger = logging.getLogger("sebba_code")


def sync_progress(state: AgentState) -> dict:
    """Sync state with on-disk roadmap changes made by tools during execution.

    Tools like mark_todo_done modify the filesystem but can't update graph state.
    This node bridges that gap by diffing the roadmap before/after execution.
    """
    logger.info("Syncing progress from roadmap")
    agent_dir = get_agent_dir()
    main_md = agent_dir / "gcc" / "main.md"

    if not main_md.exists():
        return {}

    roadmap = main_md.read_text()
    previous_roadmap = state.get("roadmap", "")

    # Find todos that are now [x] but weren't before
    newly_completed = []
    for match in re.finditer(r"- \[x\] ~~(.+?)~~", roadmap):
        todo_text = match.group(1).strip()
        # Check this wasn't already completed in the previous roadmap snapshot
        if f"- [x] ~~{todo_text}~~" not in previous_roadmap:
            newly_completed.append(todo_text)

    previous = list(state.get("todos_completed_this_session", []))
    return {
        "todos_completed_this_session": previous + newly_completed,
        "roadmap": roadmap,
    }


def extract_session(state: AgentState) -> dict:
    """Read GCC commits from this session, distill into lasting memory."""
    logger.info("Extracting session commits into lasting memory")
    agent_dir = get_agent_dir()
    commits_dir = agent_dir / "gcc" / "commits"
    start = state.get("session_start_commit", 0)
    all_commits = sorted(commits_dir.glob("*.md")) if commits_dir.exists() else []
    session_commits = all_commits[start:]

    if not session_commits:
        return {}

    combined = "\n\n---\n\n".join(f.read_text() for f in session_commits)

    extraction_prompt = f"""Read these session commits and extract lasting knowledge.

## Session Commits
{combined}

## Current Memory Index
{state["memory"]["l0_index"]}

## Todos Completed
{chr(10).join(f'- {t}' for t in state.get('todos_completed_this_session', []))}

Extract JSON:
{{
  "memory_updates": [
    {{"file": "architecture/auth-system.md", "action": "create|append|replace_section", "section": "optional", "content": "..."}}
  ],
  "index_updates": [
    {{"old_line": "existing line or null", "new_line": "updated summary"}}
  ],
  "new_rules": [
    {{"file": "rules/auth-middleware.md", "paths": ["apps/api/src/middleware/**"], "content": "rule text"}}
  ]
}}

Rules:
- Only extract genuinely NEW knowledge not already in memory
- Decisions from exploration branches are especially valuable
- Keep index lines under 100 characters
- Empty lists if nothing new was learned
"""

    llm = get_llm()
    if DEBUG_PROMPTS:
        logger.debug("── extraction prompt (%d chars) ──\n%s", len(extraction_prompt), extraction_prompt[:2000])
    response = llm.invoke(extraction_prompt)
    updates = parse_json(response.content)

    apply_memory_updates(updates.get("memory_updates", []))
    apply_index_updates(updates.get("index_updates", []))
    apply_new_rules(updates.get("new_rules", []))

    # Write session summary
    from datetime import date

    session_file = agent_dir / "sessions" / f"{date.today().isoformat()}.md"
    append_or_create(
        session_file, format_session_from_commits(session_commits, updates)
    )

    # Advance the commit pointer so we don't re-extract on the next loop iteration
    return {"session_start_commit": len(all_commits)}


def should_continue(state: AgentState) -> str:
    logger.info("Checking if session should continue")
    completed = len(state.get("todos_completed_this_session", []))
    if completed >= 5:
        return "no"
    if state.get("current_todo") is not None:
        return "yes"
    return "no"
