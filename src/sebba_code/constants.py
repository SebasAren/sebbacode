"""Global constants and agent directory management."""

from pathlib import Path

AGENT_DIR = Path(".agent")
DEBUG_PROMPTS = False


def init_agent_dir(path: Path) -> None:
    """Override the global AGENT_DIR. Called once at startup."""
    global AGENT_DIR
    AGENT_DIR = path


def get_agent_dir() -> Path:
    return AGENT_DIR


def set_debug_prompts(enabled: bool) -> None:
    global DEBUG_PROMPTS
    DEBUG_PROMPTS = enabled
