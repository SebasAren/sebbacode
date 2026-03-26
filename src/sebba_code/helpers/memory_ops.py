"""Provides memory file update operations for knowledge persistence.

L1 writes (apply_memory_updates) now delegate to the memory.layer pipeline:
  memory.layer.write_l2()  →  L2 detail
  memory.hook fires async   →  L1 summary from L2

The old direct-L1-write behaviour of apply_memory_updates() has been removed.
All session extraction now flows through sebba_code.memory.layers.MemoryLayer.

Remaining operations (not changed):
  - apply_index_updates  : update L0 _index.md
  - apply_new_rules      : write rules/ verbatim
  - append_or_create     : append session summaries to sessions/
  - format_session_from_summaries : format a session summary string
"""

from datetime import date
from pathlib import Path

from sebba_code.constants import get_agent_dir


# ──────────────────────────────────────────────────────────────────────────────
# Memory persistence — delegates to MemoryLayer (no direct L1 writes)
# ──────────────────────────────────────────────────────────────────────────────

def apply_memory_updates(updates: list[dict]) -> None:
    """Apply memory file updates from extract_session.

    This function has been refactored to write ALL content to L2 only.
    A background hook (post_extraction_hook) will asynchronously generate
    L1 summaries from the L2 entries — L1 is never written directly here.

    Args:
        updates: List of dicts with keys: file, content, action, source

    No L1 files are written by this function.
    """
    from sebba_code.memory.layers import MemoryLayer

    layer = MemoryLayer()

    for update in updates:
        action = update.get("action", "create")
        content = update.get("content", "")
        if not content.strip():
            continue

        # Index-only / rule-only actions are handled by apply_index_updates
        # and apply_new_rules respectively.
        if action in ("update_index", "append_rules"):
            continue

        # Derive topic from the file key (memory/architecture.md → architecture)
        file_key = update.get("file", "session")
        topic = Path(file_key).stem or "session"

        layer.write_l2(content, topic)

    logger = __import__("logging").getLogger("sebba_code")
    logger.debug("apply_memory_updates: wrote %d L2 entries (L1 via async hook)", len(updates))


# ──────────────────────────────────────────────────────────────────────────────
# Index / rules / session helpers (unchanged)
# ──────────────────────────────────────────────────────────────────────────────

def apply_index_updates(updates: list[dict]) -> None:
    """Update lines in the L0 _index.md file."""
    index_path = get_agent_dir() / "memory" / "_index.md"
    if not index_path.exists():
        return

    content = index_path.read_text()
    for update in updates:
        if isinstance(update, str):
            # LLM sometimes returns plain strings — treat as new_line append
            content = content.rstrip() + "\n" + update + "\n"
            continue
        old_line = update.get("old_line")
        new_line = update.get("new_line", "")
        if not new_line:
            continue
        if old_line and old_line in content:
            content = content.replace(old_line, new_line, 1)
        else:
            content = content.rstrip() + "\n" + new_line + "\n"

    index_path.write_text(content)


def apply_new_rules(rules: list[dict]) -> None:
    """Write new rule files from extract_session.

    Rules are written verbatim (not summarised) because they contain
    imperative path-scoped instructions that must be preserved exactly.
    """
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
    """Append to a file, creating it if it doesn't exist.

    Used for session summaries under sessions/.
    """
    filepath.parent.mkdir(parents=True, exist_ok=True)
    if filepath.exists():
        existing = filepath.read_text()
        filepath.write_text(existing + "\n\n---\n\n" + content)
    else:
        filepath.write_text(content)


def format_session_from_summaries(
    summaries: list[dict], updates: dict
) -> str:
    """Format a session summary from todo summaries and extracted updates."""
    parts = [f"# Session Summary — {date.today().isoformat()}\n"]

    parts.append("## Completed Todos")
    for s in summaries:
        parts.append(f"- {s['summary']}")

    if updates.get("memory_updates"):
        parts.append("\n## Memory Updates")
        for m in updates["memory_updates"]:
            parts.append(f"- {m['action']}: {m['file']}")

    if updates.get("new_rules"):
        parts.append("\n## New Rules")
        for r in updates["new_rules"]:
            parts.append(f"- {r['file']}")

    return "\n".join(parts)
