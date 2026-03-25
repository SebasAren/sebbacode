"""Provides file discovery and relevance filtering utilities for memory retrieval."""

from pathlib import Path


def list_available_files(directory: Path, depth: int = 1) -> str:
    """List markdown files in a directory up to a given depth."""
    if not directory.exists():
        return "(empty)"

    files = []
    for f in sorted(directory.rglob("*.md")):
        rel = f.relative_to(directory)
        if rel.name == "_index.md":
            continue  # L0 index, not an L1 file
        if len(rel.parts) <= depth:
            files.append(str(rel))

    return "\n".join(f"- {f}" for f in files) if files else "(empty)"


def summarize_memory_files(directory: Path, max_lines_per_file: int = 3) -> str:
    """List memory files with brief content previews, grouped by tier."""
    if not directory.exists():
        return "(no memory files yet)"

    l1_entries: list[str] = []
    l2_entries: list[str] = []

    for f in sorted(directory.rglob("*.md")):
        rel = f.relative_to(directory)
        if rel.name == "_index.md":
            continue
        try:
            lines = [l.strip() for l in f.read_text().splitlines() if l.strip()]
            preview = " / ".join(lines[:max_lines_per_file]) if lines else "(empty)"
        except Exception:
            preview = "(unreadable)"
        entry = f"- {rel}: {preview}"
        if len(rel.parts) == 1:
            l1_entries.append(entry)
        else:
            l2_entries.append(entry)

    parts: list[str] = []
    if l1_entries:
        parts.append("L1 (broad overviews):\n" + "\n".join(l1_entries))
    if l2_entries:
        parts.append("L2 (deep-dive, topic-specific):\n" + "\n".join(l2_entries))
    return "\n\n".join(parts) if parts else "(no memory files yet)"


def summarize_rules(rules_dir: Path) -> str:
    """List existing rule files with their path scopes and content preview."""
    if not rules_dir.exists():
        return "(no rules yet)"

    from sebba_code.helpers.rules_ops import parse_path_frontmatter, strip_frontmatter

    entries: list[str] = []
    for f in sorted(rules_dir.rglob("*.md")):
        rel = f.relative_to(rules_dir)
        try:
            content = f.read_text()
            paths = parse_path_frontmatter(content)
            body = strip_frontmatter(content).strip()
            preview = body[:120].replace("\n", " ")
            scope = f"paths: {', '.join(paths)}" if paths else "global"
            entries.append(f"- {rel} ({scope}): {preview}")
        except Exception:
            entries.append(f"- {rel}: (unreadable)")

    return "\n".join(entries) if entries else "(no rules yet)"


def is_relevant(filename: str, todo_text: str) -> bool:
    """Quick heuristic: does the filename seem relevant to the todo text?"""
    stem = Path(filename).stem.lower().replace("-", " ").replace("_", " ")
    words = set(stem.split())
    todo_words = set(todo_text.lower().split())
    return bool(words & todo_words)
