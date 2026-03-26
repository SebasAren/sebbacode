"""Codebase search tools — glob and grep for file/code discovery."""

import subprocess
from pathlib import Path

from langchain_core.tools import tool


@tool
def search_files(pattern: str, path: str = ".") -> str:
    """Find files matching a glob pattern.

    Args:
        pattern: Glob pattern (e.g. "**/*.py", "src/**/test_*.py")
        path: Directory to search from (default: current directory)
    """
    base = Path(path)
    if not base.exists():
        return f"Error: {path} does not exist"

    matches = []
    for p in sorted(base.glob(pattern)):
        if any(part in str(p) for part in [".git", "node_modules", "__pycache__", ".venv"]):
            continue
        matches.append(str(p))
        if len(matches) >= 50:
            break

    if not matches:
        return f"No files matching '{pattern}' in {path}"
    result = "\n".join(matches)
    if len(matches) == 50:
        result += "\n... (truncated at 50 results)"
    return result


@tool
def search_code(query: str, glob: str = "", path: str = ".") -> str:
    """Search file contents using grep.

    Args:
        query: Text or regex pattern to search for
        glob: Optional file glob filter (e.g. "*.py")
        path: Directory to search from (default: current directory)
    """
    cmd = ["grep", "-rn", "--color=never"]
    if glob:
        cmd.extend(["--include", glob])
    # Exclude common non-source directories
    for exclude in [".git", "node_modules", "__pycache__", ".venv"]:
        cmd.extend(["--exclude-dir", exclude])
    cmd.extend([query, path])

    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=30,
        )
        output = result.stdout
        if not output:
            return f"No matches for '{query}'" + (f" in {glob} files" if glob else "")
        if len(output) > 5000:
            output = output[:5000] + "\n... (truncated)"
        return output
    except subprocess.TimeoutExpired:
        return "Error: search timed out after 30s"
    except Exception as e:
        return f"Error: {e}"
