"""Implements the file reading, writing, and shell command execution tools for agents."""

import subprocess
from pathlib import Path

from langchain_core.tools import tool


@tool
def read_file(path: str) -> str:
    """Read the contents of a file.

    Args:
        path: Path to the file to read
    """
    p = Path(path)
    if not p.exists():
        return f"Error: {path} does not exist"
    if not p.is_file():
        return f"Error: {path} is not a file"
    try:
        content = p.read_text()
        if len(content) > 10000:
            return content[:10000] + f"\n\n... (truncated, {len(content)} total chars)"
        return content
    except Exception as e:
        return f"Error reading {path}: {e}"


@tool
def write_file(path: str, content: str) -> str:
    """Write content to a file, creating parent directories if needed.

    Args:
        path: Path to the file to write
        content: Content to write
    """
    p = Path(path)
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content)
        return f"Wrote {len(content)} chars to {path}"
    except Exception as e:
        return f"Error writing {path}: {e}"


@tool
def run_command(command: str, cwd: str = ".") -> str:
    """Run a shell command and return its output.

    Args:
        command: The command to run
        cwd: Working directory (default: current directory)
    """
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=120,
            cwd=cwd,
        )
        output = ""
        if result.stdout:
            output += result.stdout
        if result.stderr:
            output += f"\nSTDERR:\n{result.stderr}"
        if result.returncode != 0:
            output += f"\nExit code: {result.returncode}"
        return output.strip() or "(no output)"
    except subprocess.TimeoutExpired:
        return "Error: command timed out after 120s"
    except Exception as e:
        return f"Error running command: {e}"
