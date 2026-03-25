"""Provides YAML frontmatter parsing for path-scoped rules."""

from pathlib import Path

import yaml


def parse_path_frontmatter(content: str) -> list[str] | None:
    """Extract path globs from YAML frontmatter. Returns None if no paths defined."""
    if not content.startswith("---"):
        return None
    parts = content.split("---", 2)
    if len(parts) < 3:
        return None
    meta = yaml.safe_load(parts[1])
    return meta.get("paths") if meta else None


def strip_frontmatter(content: str) -> str:
    """Remove YAML frontmatter from markdown content."""
    if not content.startswith("---"):
        return content
    parts = content.split("---", 2)
    return parts[2].strip() if len(parts) >= 3 else content


def find_nearest_agent_dir(filepath: str) -> Path:
    """Walk up from filepath to find the nearest .agent/ directory."""
    from sebba_code.constants import AGENT_DIR

    p = Path(filepath).parent
    while p != p.parent:
        if (p / ".agent").is_dir():
            return p / ".agent"
        p = p.parent
    return AGENT_DIR
