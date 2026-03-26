"""Pre-planning reconnaissance — populates state with codebase context before plan_draft."""

import logging
import subprocess

from sebba_code.constants import get_agent_dir
from sebba_code.helpers.rules_ops import parse_path_frontmatter, strip_frontmatter
from sebba_code.state import AgentState

logger = logging.getLogger("sebba_code")


def plan_recon(state: AgentState) -> dict:
    """Load file structure, L1 memory, and global rules before planning."""
    logger.info("plan_recon: loading codebase context for planner")
    agent_dir = get_agent_dir()
    memory = state.get("memory", {})

    # 1. File structure snapshot
    tree_output = subprocess.run(
        [
            "find", ".", "-maxdepth", "3",
            "-not", "-path", "./.git/*",
            "-not", "-path", "*/node_modules/*",
            "-not", "-path", "*/__pycache__/*",
            "-not", "-path", "*/.venv/*",
        ],
        capture_output=True,
        text=True,
    ).stdout

    briefing = f"## File Structure\n```\n{tree_output[:4000]}\n```"

    # 2. Load L1 memory files (top-level .md in .agent/memory/)
    memory_dir = agent_dir / "memory"
    l1_files = dict(memory.get("l1_files", {}))
    if memory_dir.exists():
        for f in sorted(memory_dir.glob("*.md")):
            if f.name == "_index.md":
                continue
            try:
                l1_files[f.stem] = f.read_text()
            except Exception:
                pass

    # 3. Load global rules (no paths: frontmatter)
    active_rules = dict(memory.get("active_rules", {}))
    rules_dir = agent_dir / "rules"
    if rules_dir.exists():
        for rule_file in sorted(rules_dir.rglob("*.md")):
            try:
                content = rule_file.read_text()
                paths = parse_path_frontmatter(content)
                if paths is None:
                    active_rules[rule_file.stem] = strip_frontmatter(content)
            except Exception:
                pass

    logger.info(
        "plan_recon: loaded %d L1 files, %d rules, %d chars of file structure",
        len(l1_files), len(active_rules), len(tree_output),
    )

    return {
        "memory": {
            **memory,
            "l1_files": l1_files,
            "active_rules": active_rules,
        },
        "briefing": briefing,
    }
