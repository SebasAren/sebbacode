"""Implements the git_commit tool for committing staged changes."""

from langchain_core.tools import tool

from sebba_code.helpers.git import git_run


@tool
def git_commit(message: str, files: list[str] | None = None) -> str:
    """Commit staged changes to git.

    Args:
        message: The commit message. Must be non-empty.
        files: Optional list of specific files to commit. If None, commits all staged changes.

    Returns:
        Output from git commit command, including any errors.
    """
    if not message or not message.strip():
        return "Error: commit message cannot be empty"

    args = ["commit", "-m", message]
    if files:
        args.append("--")
        args.extend(files)

    result = git_run(args)

    output = ""
    if result.stdout:
        output += result.stdout
    if result.stderr:
        output += f"\nSTDERR:\n{result.stderr}"
    if result.returncode != 0:
        output += f"\nExit code: {result.returncode}"
    return output.strip() or "(no output)"
