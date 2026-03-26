"""Provides git utility functions for branch detection."""

import subprocess
from pathlib import Path


def git_run(args: list[str], cwd: str | Path | None = None) -> subprocess.CompletedProcess:
    """Run a git command and return the result."""
    return subprocess.run(
        ["git", *args],
        capture_output=True,
        text=True,
        cwd=cwd,
    )


def get_current_branch(cwd: str | Path | None = None) -> str:
    """Get the current git branch name."""
    result = git_run(["rev-parse", "--abbrev-ref", "HEAD"], cwd=cwd)
    return result.stdout.strip()
