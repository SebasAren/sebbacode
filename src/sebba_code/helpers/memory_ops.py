"""Provides memory file update operations for session extraction and knowledge persistence."""

from datetime import date
from pathlib import Path

from sebba_code.constants import get_agent_dir


def apply_memory_updates(updates: list[dict]) -> None:
    """Apply memory file updates from extract_session."""
    memory_dir = get_agent_dir() / "memory"

    for update in updates:
        filepath = memory_dir / update["file"]
        filepath.parent.mkdir(parents=True, exist_ok=True)
        action = update.get("action", "create")

        if action == "create":
            filepath.write_text(update["content"])
        elif action == "append":
            existing = filepath.read_text() if filepath.exists() else ""
            filepath.write_text(existing + "\n" + update["content"])
        elif action == "replace_section":
            if filepath.exists():
                from sebba_code.helpers.markdown import replace_section

                content = filepath.read_text()
                content = replace_section(
                    content, f"## {update['section']}", update["content"]
                )
                filepath.write_text(content)
            else:
                filepath.write_text(update["content"])


def apply_index_updates(updates: list[dict]) -> None:
    """Update lines in the L0 _index.md file."""
    index_path = get_agent_dir() / "memory" / "_index.md"
    if not index_path.exists():
        return

    content = index_path.read_text()
    for update in updates:
        old_line = update.get("old_line")
        new_line = update["new_line"]
        if old_line and old_line in content:
            content = content.replace(old_line, new_line, 1)
        else:
            content = content.rstrip() + "\n" + new_line + "\n"

    index_path.write_text(content)


def apply_new_rules(rules: list[dict]) -> None:
    """Write new rule files from extract_session."""
    agent_dir = get_agent_dir()

    for rule in rules:
        rule_path = agent_dir / rule["file"]
        rule_path.parent.mkdir(parents=True, exist_ok=True)
        content = ""
        if rule.get("paths"):
            content = "---\npaths:\n"
            for p in rule["paths"]:
                content += f'  - "{p}"\n'
            content += "---\n"
        content += rule["content"]
        rule_path.write_text(content)



def append_or_create(filepath: Path, content: str) -> None:
    """Append to a file, creating it if it doesn't exist."""
    filepath.parent.mkdir(parents=True, exist_ok=True)
    if filepath.exists():
        existing = filepath.read_text()
        filepath.write_text(existing + "\n\n---\n\n" + content)
    else:
        filepath.write_text(content)


def format_session_from_commits(
    commit_files: list[Path], updates: dict
) -> str:
    """Format a session summary from commits and extracted updates."""
    parts = [f"# Session Summary — {date.today().isoformat()}\n"]

    parts.append("## Commits")
    for f in commit_files:
        first_line = f.read_text().split("\n", 1)[0]
        parts.append(f"- {first_line}")

    if updates.get("memory_updates"):
        parts.append("\n## Memory Updates")
        for m in updates["memory_updates"]:
            parts.append(f"- {m['action']}: {m['file']}")

    if updates.get("new_rules"):
        parts.append("\n## New Rules")
        for r in updates["new_rules"]:
            parts.append(f"- {r['file']}")

    return "\n".join(parts)


def remove_active_branch(explore_id: str) -> None:
    """Remove an exploration from the Active Branches section of main.md."""
    main_md = get_agent_dir() / "gcc" / "main.md"
    if not main_md.exists():
        return

    content = main_md.read_text()
    lines = content.split("\n")
    filtered = [l for l in lines if explore_id not in l]
    main_md.write_text("\n".join(filtered))
