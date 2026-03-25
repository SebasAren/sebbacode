"""Provides file discovery and relevance filtering utilities for memory retrieval."""

from pathlib import Path


def list_available_files(directory: Path, depth: int = 1) -> str:
    """List markdown files in a directory up to a given depth."""
    if not directory.exists():
        return "(empty)"

    files = []
    for f in sorted(directory.rglob("*.md")):
        rel = f.relative_to(directory)
        if len(rel.parts) <= depth:
            files.append(str(rel))

    return "\n".join(f"- {f}" for f in files) if files else "(empty)"


def is_relevant(filename: str, todo_text: str) -> bool:
    """Quick heuristic: does the filename seem relevant to the todo text?"""
    stem = Path(filename).stem.lower().replace("-", " ").replace("_", " ")
    words = set(stem.split())
    todo_words = set(todo_text.lower().split())
    return bool(words & todo_words)
