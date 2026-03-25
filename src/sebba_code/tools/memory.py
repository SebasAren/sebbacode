"""Implements the memory search tool for querying agent memory context."""

import subprocess
from pathlib import Path

from langchain_core.tools import tool

from sebba_code.constants import get_agent_dir
from sebba_code.llm import get_llm


@tool
def memory_query(question: str) -> str:
    """Search agent memory for context. Uses git grep + LLM judgment.

    Args:
        question: What you want to know from memory
    """
    agent_dir = get_agent_dir()
    index_path = agent_dir / "memory" / "_index.md"
    index = index_path.read_text() if index_path.exists() else "(empty)"

    first_word = question.split()[0] if question.split() else ""
    grep = ""
    if first_word:
        result = subprocess.run(
            ["git", "grep", "-l", "-i", first_word, "--", str(agent_dir)],
            capture_output=True,
            text=True,
        )
        grep = result.stdout

    git_log = subprocess.run(
        ["git", "log", "--oneline", "-20", "--", str(agent_dir / "memory")],
        capture_output=True,
        text=True,
    ).stdout

    prompt = (
        f"Question: {question}\n\n"
        f"Memory index:\n{index}\n\n"
        f"Files matching:\n{grep}\n\n"
        f"Recent changes:\n{git_log}\n\n"
        f"Which file(s) to read? Return file paths, one per line."
    )

    llm = get_llm()
    response = llm.invoke(prompt)
    paths = [p.strip() for p in response.content.strip().split("\n") if p.strip()]

    parts = []
    for p in paths:
        full = Path(p)
        if full.exists():
            parts.append(f"### {p}\n{full.read_text()}")

    return "\n\n".join(parts) if parts else "No relevant memory found."
