"""Implements the rule matching node for loading path-scoped rules."""

import logging
from fnmatch import fnmatch

from sebba_code.constants import get_agent_dir
from sebba_code.helpers.rules_ops import (
    find_nearest_agent_dir,
    parse_path_frontmatter,
    strip_frontmatter,
)
from sebba_code.state import AgentState


logger = logging.getLogger("sebba_code")


def match_rules(state: AgentState) -> dict:
    """Load path-scoped rules matching the target files."""
    logger.info("Matching path-scoped rules to target files")
    agent_dir = get_agent_dir()
    target_files = state["target_files"]
    memory = state["memory"]
    active_rules = {}

    # Collect rule directories: root + per-app
    rule_dirs = [agent_dir / "rules"]
    seen = set()
    for target_file in target_files:
        nearest = find_nearest_agent_dir(target_file)
        rd = nearest / "rules"
        if rd.exists() and str(rd) not in seen:
            seen.add(str(rd))
            rule_dirs.append(rd)

    for rules_dir in rule_dirs:
        if not rules_dir.exists():
            continue
        for rule_file in rules_dir.glob("**/*.md"):
            content = rule_file.read_text()
            paths = parse_path_frontmatter(content)

            if paths is None:
                # Global rule — always loaded
                active_rules[rule_file.stem] = strip_frontmatter(content)
            elif any(fnmatch(f, p) for p in paths for f in target_files):
                active_rules[rule_file.stem] = strip_frontmatter(content)

    return {"memory": {**memory, "active_rules": active_rules}}
