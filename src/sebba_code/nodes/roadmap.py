"""Implements the roadmap parsing node for todo extraction and status checking."""

import logging
import re

from sebba_code.constants import get_agent_dir
from sebba_code.state import AgentState


logger = logging.getLogger("sebba_code")


def read_roadmap(state: AgentState) -> dict:
    """Parse main.md, extract todos and target files, pick next todo."""
    logger.info("Reading roadmap from main.md")
    main_md = get_agent_dir() / "roadmap.md"

    if not main_md.exists():
        return {"roadmap": "", "current_todo": None, "target_files": []}

    roadmap = main_md.read_text()

    # Parse todos
    todos = []
    for i, match in enumerate(re.finditer(r"- \[([ x])\] (.+)", roadmap)):
        todos.append(
            {
                "text": match.group(2).strip(),
                "done": match.group(1) == "x",
                "index": i,
            }
        )

    current_todo = next((t for t in todos if not t["done"]), None)

    # Parse target files section
    target_files = []
    in_targets = False
    for line in roadmap.split("\n"):
        if line.strip().lower().startswith("## target files"):
            in_targets = True
            continue
        if in_targets and line.startswith("##"):
            break
        if in_targets and line.strip().startswith("- "):
            target_files.append(line.strip().lstrip("- ").strip())

    return {
        "roadmap": roadmap,
        "current_todo": current_todo,
        "target_files": target_files,
    }


def has_todo(state: AgentState) -> str:
    logger.info("Checking if there is a pending todo")
    return "no" if state.get("current_todo") is None else "yes"


def is_first_todo(state: AgentState) -> str:
    """Is this the first unchecked todo (fresh roadmap)?"""
    logger.info("Checking if current todo is the first")
    roadmap = state.get("roadmap", "")
    if "- [x]" not in roadmap and state.get("current_todo"):
        return "yes"
    todo = state.get("current_todo")
    if todo and todo["index"] == 0:
        return "yes"
    return "no"
