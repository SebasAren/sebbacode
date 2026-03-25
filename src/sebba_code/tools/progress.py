"""Implements GCC commit, todo management, and roadmap tools for progress tracking."""

from datetime import datetime

from langchain_core.tools import tool

from sebba_code.constants import get_agent_dir
from sebba_code.helpers.markdown import append_to_section


@tool
def gcc_commit(
    summary: str,
    what_i_did: str,
    decisions_made: str = "",
    issues_encountered: str = "",
    files_touched: str = "",
) -> str:
    """Log structured progress. Call after completing a meaningful unit of work.

    Args:
        summary: One-line summary
        what_i_did: Bullet list of actions taken
        decisions_made: Any choices made and why
        issues_encountered: Problems hit and how resolved
        files_touched: Files created/modified with brief notes
    """
    commits_dir = get_agent_dir() / "gcc" / "commits"
    commits_dir.mkdir(parents=True, exist_ok=True)

    num = len(list(commits_dir.glob("*.md"))) + 1

    content = (
        f"# Commit {num:03d}: {summary}\n"
        f"**Date**: {datetime.now().isoformat()}\n\n"
        f"## What I Did\n{what_i_did}\n"
    )
    if decisions_made:
        content += f"\n## Decisions Made\n{decisions_made}\n"
    if issues_encountered:
        content += f"\n## Issues Encountered\n{issues_encountered}\n"
    if files_touched:
        content += f"\n## Files Touched\n{files_touched}\n"

    (commits_dir / f"{num:03d}.md").write_text(content)
    return f"Committed {num:03d}: {summary}"


@tool
def mark_todo_done(todo_text: str, notes: str = "") -> str:
    """Mark a todo as completed in the roadmap.

    Args:
        todo_text: Text of the todo to mark done (partial match supported)
        notes: Optional completion notes
    """
    import re

    main_md = get_agent_dir() / "gcc" / "main.md"
    content = main_md.read_text()
    suffix = f" → {notes}" if notes else ""

    # Try exact match first
    old = f"- [ ] {todo_text}"
    if old in content:
        new = f"- [x] ~~{todo_text}~~{suffix}"
        content = content.replace(old, new, 1)
        main_md.write_text(content)
        return f"Done: {todo_text}"

    # Fuzzy: find unchecked todos and match by substring containment
    unchecked = list(re.finditer(r"^- \[ \] (.+)$", content, re.MULTILINE))
    if not unchecked:
        return f"Not found (no unchecked todos): {todo_text}"

    # Score by how much of todo_text appears in each candidate
    query = todo_text.lower().strip()
    best_match = None
    best_score = 0
    for m in unchecked:
        candidate = m.group(1).strip()
        candidate_lower = candidate.lower()
        # Check if query is a substring or candidate is a substring of query
        if query in candidate_lower or candidate_lower in query:
            score = len(candidate)
            if score > best_score:
                best_score = score
                best_match = m

    if best_match:
        matched_text = best_match.group(1).strip()
        old_line = best_match.group(0)
        new_line = f"- [x] ~~{matched_text}~~{suffix}"
        content = content.replace(old_line, new_line, 1)
        main_md.write_text(content)
        return f"Done: {matched_text}"

    return f"Not found: {todo_text}"


@tool
def add_todo(todo_text: str, after: str = "") -> str:
    """Add a genuinely NEW sub-task to the roadmap. Do NOT use this to re-add
    or rephrase existing todos — use mark_todo_done to complete them instead.

    Args:
        todo_text: The new todo text (must not duplicate an existing todo)
        after: Optional text of an existing todo to insert after
    """
    main_md = get_agent_dir() / "gcc" / "main.md"
    content = main_md.read_text()

    # Reject if a similar todo already exists
    query = todo_text.lower().strip()
    for line in content.split("\n"):
        stripped = line.strip().lower()
        if stripped.startswith("- [ ] ") or stripped.startswith("- [x] "):
            existing = stripped.split("] ", 1)[1]
            if query in existing or existing in query:
                return f"Skipped (similar todo exists): {line.strip()}"

    new_line = f"- [ ] {todo_text}"
    if after:
        lines = content.split("\n")
        for i, line in enumerate(lines):
            if after in line:
                lines.insert(i + 1, new_line)
                break
        content = "\n".join(lines)
    else:
        content = append_to_section(content, "## Todos", new_line)
    main_md.write_text(content)
    return f"Added: {todo_text}"


@tool
def discover_files(files: list[str]) -> str:
    """Register additional target files found during work.

    Args:
        files: List of file paths to add to the target files section
    """
    main_md = get_agent_dir() / "gcc" / "main.md"
    content = main_md.read_text()
    added = 0
    for f in files:
        if f not in content:
            content = append_to_section(content, "## Target Files", f"- {f}")
            added += 1
    main_md.write_text(content)
    return f"Added {added} target files."
