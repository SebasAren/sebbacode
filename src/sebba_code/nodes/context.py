"""Implements the context deepening node for L1/L2 memory retrieval."""

import logging

from pydantic import BaseModel

from sebba_code.constants import DEBUG_PROMPTS, get_agent_dir
from sebba_code.helpers.files import is_relevant, list_available_files
from sebba_code.llm import get_llm, invoke_structured
from sebba_code.state import AgentState


class FileSelection(BaseModel):
    """LLM-selected list of memory file paths to load."""
    paths: list[str]


logger = logging.getLogger("sebba_code")


def deepen_context(state: AgentState) -> dict:
    """LLM picks relevant L1/L2 memory. Also loads session history from state."""
    logger.info("Deepening context with L1/L2 memory and session history")
    agent_dir = get_agent_dir()
    memory = state["memory"]
    todo = state["current_todo"]

    retrieval_prompt = f"""You are preparing context for a coding task.

Current todo: {todo["text"]}
Target files: {state["target_files"]}

Memory index (L0):
{memory["l0_index"]}

Available memory files (L1 top-level, L2 in subdirs):
{list_available_files(agent_dir / "memory", depth=2)}

Return JSON: {{"paths": ["relative/path1.md", ...]}}. Be selective.
"""

    llm = get_llm()
    if DEBUG_PROMPTS:
        logger.debug("── retrieval prompt (%d chars) ──\n%s", len(retrieval_prompt), retrieval_prompt[:2000])
    result = invoke_structured(llm, FileSelection, retrieval_prompt)
    requested = result.get("paths", [])

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

    # Build session history from previous todo summaries in state
    session_history = ""
    summaries = state.get("todo_summaries", [])
    if summaries:
        last = summaries[-1]
        session_history = (
            f"## Previous Todo: {last['summary']}\n\n"
            f"### What was done\n{last['what_i_did']}\n"
        )
        if last.get("decisions_made"):
            session_history += f"\n### Decisions Made\n{last['decisions_made']}\n"

    # Load branch context if on a feature branch
    branch = state.get("working_branch", "main")
    branch_dir = agent_dir / "branches" / branch
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
