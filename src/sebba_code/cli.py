"""Command-line interface commands for the agent."""

import logging
import re
import subprocess
from pathlib import Path

import click

from sebba_code.config import load_config
from sebba_code.constants import get_agent_dir, init_agent_dir, set_debug_prompts
from sebba_code.llm import configure_llm

logger = logging.getLogger("sebba_code")


@click.group()
@click.option("--agent-dir", default=".agent", help="Path to .agent directory")
def cli(agent_dir: str):
    """LangGraph coding agent with git-native memory."""
    init_agent_dir(Path(agent_dir))


@cli.command()
def init():
    """Create the .agent/ directory structure."""
    from sebba_code.seed import init_agent_structure

    init_agent_structure()
    click.echo(f"Initialized {get_agent_dir()}/")


def _configure_llm_from_config():
    """Load config and configure LLM instances."""
    config = load_config(get_agent_dir())
    configure_llm(
        model=config.llm.model,
        model_provider=config.llm.model_provider,
        base_url=config.llm.base_url,
        api_key=config.llm.api_key,
        cheap_model=config.llm.cheap_model,
        cheap_model_provider=config.llm.cheap_model_provider,
        cheap_base_url=config.llm.cheap_base_url,
        cheap_api_key=config.llm.cheap_api_key,
    )


def _get_next_todo() -> str | None:
    """Parse roadmap and return the first uncompleted todo, or None if all done."""
    roadmap_path = get_agent_dir() / "gcc" / "main.md"
    if not roadmap_path.exists():
        return None

    with open(roadmap_path) as f:
        content = f.read()

    # Parse multiline todos: each - [ ] item may span multiple lines
    # A todo line starts with '- [ ]' (possibly with leading whitespace)
    lines = content.split("\n")
    todo_lines = []
    capturing = False

    for line in lines:
        stripped = line.strip()
        if stripped.startswith("- [ ]"):
            # Start of a new uncompleted todo
            todo_lines = [stripped[6:].strip()]  # Remove "- [ ]" prefix
            capturing = True
        elif capturing:
            if stripped.startswith("- [") or stripped.startswith("##"):
                # Next todo or new section - stop capturing
                break
            elif stripped:  # Continuation line
                todo_lines.append(stripped)
            # Empty lines are part of the todo, keep capturing

    if todo_lines:
        return " ".join(todo_lines)
    return None


def _count_todos() -> tuple[int, int]:
    """Parse roadmap and return (completed, pending) todo counts."""
    roadmap_path = get_agent_dir() / "gcc" / "main.md"
    if not roadmap_path.exists():
        return 0, 0

    with open(roadmap_path) as f:
        content = f.read()

    completed = 0
    pending = 0
    # Match checkbox lines: - [x] or - [ ] at start of line (with optional leading whitespace)
    pattern = re.compile(r"^\s*[-*]\s*\[([ x])\]")
    
    for line in content.split("\n"):
        match = pattern.match(line)
        if match:
            if match.group(1) == "x":
                completed += 1
            else:
                pending += 1

    return completed, pending


def _count_gcc_commits() -> int | None:
    """Count total GCC commits in the repository. Returns None if not a git repo."""
    try:
        result = subprocess.run(
            ["git", "rev-list", "--count", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
        )
        return int(result.stdout.strip())
    except (subprocess.CalledProcessError, FileNotFoundError, ValueError):
        return None


def _list_memory_files() -> list[Path]:
    """Return sorted list of files in .agent/memory/ directory."""
    memory_dir = get_agent_dir() / "memory"
    if not memory_dir.exists():
        return []
    return sorted(
        f.relative_to(memory_dir) 
        for f in memory_dir.rglob("*") 
        if f.is_file()
    )


@cli.command()
def status():
    """Print a summary of the current agent state."""
    # Todo counts
    completed, pending = _count_todos()
    
    # GCC commits
    gcc_commits = _count_gcc_commits()
    
    # Memory files
    memory_files = _list_memory_files()

    click.echo("=== Agent Status ===\n")
    
    # Roadmap section
    click.echo("Roadmap (.agent/gcc/main.md):")
    if completed == 0 and pending == 0:
        click.echo("  (no roadmap found)\n")
    else:
        click.echo(f"  Completed: {completed}")
        click.echo(f"  Pending:   {pending}\n")
    
    # GCC commits section
    click.echo("GCC Commits:")
    if gcc_commits is not None:
        click.echo(f"  Total: {gcc_commits}\n")
    else:
        click.echo("  (not a git repository)\n")
    
    # Memory files section
    click.echo("Memory Files (.agent/memory/):")
    if memory_files:
        for f in memory_files:
            click.echo(f"  {f}")
    else:
        click.echo("  (no memory files)")


@cli.command()
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose logging")
@click.option("--dry-run", is_flag=True, help="Print next roadmap todo and exit")
@click.option("--debug-prompts", is_flag=True, help="Log prompts and message summaries at each LLM call")
def run(verbose: bool, dry_run: bool, debug_prompts: bool):
    """Execute the agent graph against the current roadmap."""
    if dry_run:
        next_todo = _get_next_todo()
        if next_todo:
            click.echo(f"Next todo: {next_todo}")
        else:
            click.echo("All tasks complete.")
        return

    logging.basicConfig(
        level=logging.WARNING,
        format="%(asctime)s [%(name)s] %(message)s",
        datefmt="%H:%M:%S",
    )
    logger.setLevel(logging.DEBUG if verbose else logging.INFO)

    if debug_prompts:
        set_debug_prompts(True)
        logging.getLogger("sebba_code.debug").setLevel(logging.DEBUG)
    _configure_llm_from_config()

    from sebba_code.graph import build_agent_graph

    graph = build_agent_graph()

    logger.info("Starting agent...")
    result = graph.invoke({"messages": []})

    completed = result.get("todos_completed_this_session", [])
    if completed:
        click.echo(f"\nCompleted {len(completed)} todos:")
        for t in completed:
            click.echo(f"  - {t}")
    else:
        click.echo("\nNo todos completed this session.")


@cli.command()
@click.argument("title")
@click.option("--description", "-d", default="", help="Issue description")
@click.option("--labels", "-l", default="", help="Issue labels")
def seed(title: str, description: str, labels: str):
    """Seed a roadmap from an issue description."""
    _configure_llm_from_config()

    from sebba_code.seed import seed_roadmap_from_issue

    seed_roadmap_from_issue(title, description, labels)
    click.echo(f"Roadmap seeded at {agent_dir}/gcc/main.md")
