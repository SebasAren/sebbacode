"""Implements the context deepening node for L1/L2 memory retrieval."""

import logging

from sebba_code.constants import DEBUG_PROMPTS, get_agent_dir
from sebba_code.helpers.files import is_relevant, list_available_files
from sebba_code.helpers.parsing import parse_json_list
from sebba_code.llm import get_llm
from sebba_code.state import AgentState


logger = logging.getLogger("sebba_code")


def deepen_context(state: AgentState) -> dict:
    """LLM picks relevant L1/L2 memory. Also loads latest GCC commit (K=1)."""
    logger.info("Deepening context with L1/L2 memory and session history")
    agent_dir = get_agent_dir()
    memory = state["memory"]
    todo = state["current_todo"]

    retrieval_prompt = f"""You are preparing context for a coding task.

Current todo: {todo["text"]}
Target files: {state["target_files"]}

Memory index (L0):
{memory["l0_index"]}

Available L1 files:
{list_available_files(agent_dir / "memory", depth=1)}

Return a JSON list of relative paths to load. Be selective.
"""

    llm = get_llm()
    if DEBUG_PROMPTS:
        logger.debug("── retrieval prompt (%d chars) ──\n%s", len(retrieval_prompt), retrieval_prompt[:2000])
    response = llm.invoke(retrieval_prompt)
    requested = parse_json_list(response.content)

    l1_files = {}
    l2_files = {}

    for filepath in requested:
        full_path = agent_dir / "memory" / filepath
        if full_path.exists():
            l1_files[filepath] = full_path.read_text()
            # Check for L2 subdirectory
            l2_dir = full_path.with_suffix("")
            if l2_dir.is_dir():
                for l2_file in l2_dir.glob("*.md"):
                    if is_relevant(l2_file.stem, todo["text"]):
                        key = str(l2_file.relative_to(agent_dir / "memory"))
                        l2_files[key] = l2_file.read_text()

    # Load latest GCC commit for session continuity (K=1)
    session_history = ""
    commits_dir = agent_dir / "gcc" / "commits"
    if commits_dir.exists():
        commits = sorted(commits_dir.glob("*.md"))
        if commits:
            session_history = commits[-1].read_text()

    # Load branch context if on a feature branch
    branch = state.get("working_branch", "main")
    branch_dir = agent_dir / "gcc" / "branches" / branch
    if branch_dir.exists() and (branch_dir / "context.md").exists():
        session_history += "\n\n" + (branch_dir / "context.md").read_text()

    return {
        "memory": {
            **memory,
            "l1_files": l1_files,
            "l2_files": l2_files,
            "session_history": session_history,
        }
    }
