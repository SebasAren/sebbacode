"""Implements the context loading node for session initialization."""

import logging

from sebba_code.constants import get_agent_dir
from sebba_code.helpers.git import get_current_branch
from sebba_code.state import AgentState


logger = logging.getLogger("sebba_code")


def load_context(state: AgentState) -> dict:
    """Load L0 index and detect git state. Runs once at session start."""
    logger.info("Loading L0 index and git state")
    agent_dir = get_agent_dir()

    l0_path = agent_dir / "memory" / "_index.md"
    l0_index = l0_path.read_text() if l0_path.exists() else ""

    branch = get_current_branch()

    return {
        "memory": {
            "l0_index": l0_index,
            "l1_files": {},
            "l2_files": {},
            "active_rules": {},
            "session_history": "",
        },
        "working_branch": branch,
        "todos_completed_this_session": [],
        "todo_summaries": [],
        "briefing": "",
        "exploration_mode": "",
    }


def needs_bootstrap(state: AgentState) -> str:
    """Check if memory needs to be bootstrapped."""
    logger.info("Checking if memory needs bootstrap")
    if not state["memory"]["l0_index"].strip():
        return "yes"
    return "no"
