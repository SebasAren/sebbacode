"""Command-line interface commands for the agent."""

import logging
import re
from pathlib import Path

import click

from sebba_code.config import load_config
from sebba_code.constants import get_agent_dir, init_agent_dir, set_debug_prompts
from sebba_code.llm import configure_llm

logger = logging.getLogger("sebba_code")

# Kept for reference, but config takes precedence
DEFAULT_PLANNING_MAX_ITERATIONS = 3


@click.group()
@click.option("--agent-dir", default=".agent", help="Path to .agent directory")
def cli(agent_dir: str):
    """LangGraph coding agent with tiered memory."""
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
    roadmap_path = get_agent_dir() / "roadmap.md"
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
    roadmap_path = get_agent_dir() / "roadmap.md"
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

    # Memory files
    memory_files = _list_memory_files()

    click.echo("=== Agent Status ===\n")

    # Roadmap section
    click.echo("Roadmap (.agent/roadmap.md):")
    if completed == 0 and pending == 0:
        click.echo("  (no roadmap found)\n")
    else:
        click.echo(f"  Completed: {completed}")
        click.echo(f"  Pending:   {pending}\n")

    # Memory files section
    click.echo("Memory Files (.agent/memory/):")
    if memory_files:
        for f in memory_files:
            click.echo(f"  {f}")
    else:
        click.echo("  (no memory files)")

    # Archived roadmaps
    archive_dir = get_agent_dir() / "roadmaps" / "archive"
    if archive_dir.exists():
        archives = sorted(archive_dir.glob("*.md"))
        if archives:
            click.echo(f"\nArchived Roadmaps ({len(archives)}):")
            for a in archives:
                click.echo(f"  {a.name}")


@cli.command()
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose logging")
@click.option("--dry-run", is_flag=True, help="Print next roadmap todo and exit")
@click.option("--debug-prompts", is_flag=True, help="Log prompts and message summaries at each LLM call")
@click.option("--max-todos", type=int, default=None, help="Override the default session limit of 5 todos")
def run(verbose: bool, dry_run: bool, debug_prompts: bool, max_todos: int | None):
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
    initial_state = {"messages": []}
    if max_todos is not None:
        initial_state["max_todos"] = max_todos
    result = graph.invoke(initial_state)

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
@click.option("--refine", is_flag=True, help="Use the planning loop for iterative refinement")
def seed(title: str, description: str, labels: str, refine: bool):
    """Seed a roadmap from an issue description.

    Use --refine to enable the planning loop for iterative draft-critique-refine
    before writing the final roadmap.
    """
    _configure_llm_from_config()

    from sebba_code.seed import init_agent_structure, seed_roadmap_from_issue

    # Ensure the agent directory structure exists
    init_agent_structure()

    if refine:
        click.echo("Using planning loop for refined roadmap...")
        seed_roadmap_from_issue(title, description, labels, use_refine=True)
    else:
        seed_roadmap_from_issue(title, description, labels, use_refine=False)

    click.echo(f"Roadmap seeded at {get_agent_dir()}/roadmap.md")


@cli.command()
@click.argument("description")
@click.option("--iterations", "-i", type=int, default=None, help="Override max planning iterations (default: from config)")
def plan(description: str, iterations: int | None):
    """Generate a roadmap using the planning loop.

    Takes a natural language description of what you want to build
    and transforms it into a structured, validated roadmap through
    an iterative draft-critique-refine cycle.
    """
    _configure_llm_from_config()

    from sebba_code.seed import init_agent_structure

    # Ensure the agent directory structure exists
    init_agent_structure()

    from sebba_code.plan_graph import build_plan_graph

    graph = build_plan_graph()

    logger.info("Starting planning loop...")

    # Build initial state for planning
    initial_state = {
        "user_request": description,
        "draft_roadmap": "",
        "planning_messages": [],
        "planning_iteration": 0,
        "planning_complete": False,
        "roadmap": "",
        "target_files": [],
        "briefing": "",
        "memory": {
            "l0_index": "",
            "l1_files": {},
            "l2_files": {},
            "active_rules": {},
            "session_history": "",
        },
    }

    # Get max iterations: CLI arg overrides config, config has its own default of 3
    max_iterations = iterations
    planning_model = None

    if iterations is None:
        # Load from config if CLI didn't override
        config = load_config(get_agent_dir())
        max_iterations = config.planning.max_iterations
        if config.planning.model:
            planning_model = config.planning.model

    # Build configurable dict for graph
    configurable = {"planning_max_iterations": max_iterations}
    if planning_model:
        configurable["planning_model"] = planning_model

    import time

    iteration = 0
    start_time = time.monotonic()

    try:
        for event in graph.stream(
            initial_state,
            config={
                "recursion_limit": 100 + max_iterations * 10,
                "configurable": configurable,
            },
        ):
            elapsed = time.monotonic() - start_time
            for node_name, node_output in event.items():
                if node_name == "draft_roadmap":
                    iteration = node_output.get("planning_iteration", 1)
                    click.echo(f"[{elapsed:.1f}s] Drafting roadmap...")
                elif node_name == "critique_roadmap":
                    complete = node_output.get("planning_complete", False)
                    status = "passed" if complete else "requesting refinement"
                    click.echo(f"[{elapsed:.1f}s] Critiquing roadmap (iteration {iteration})... {status}")
                elif node_name == "refine_roadmap":
                    iteration = node_output.get("planning_iteration", iteration)
                    click.echo(f"[{elapsed:.1f}s] Refining roadmap (iteration {iteration}/{max_iterations})...")
                elif node_name == "write_roadmap":
                    click.echo(f"[{elapsed:.1f}s] Writing final roadmap...")
    except NotImplementedError as e:
        click.echo(f"Streaming not supported: {e}")
        click.echo("Falling back to non-streaming mode...")

        result = graph.invoke(
            initial_state,
            config={
                "recursion_limit": 100 + max_iterations * 10,
                "configurable": configurable,
            },
        )

        if result.get("planning_complete"):
            click.echo(f"\nPlanning complete after {result.get('planning_iteration', '?')} iterations.")
        if result.get("draft_roadmap"):
            click.echo(f"Generated roadmap with {len(result['draft_roadmap'])} characters.")

    elapsed = time.monotonic() - start_time
    click.echo(f"[{elapsed:.1f}s] Roadmap created at {get_agent_dir()}/roadmap.md")


if __name__ == "__main__":
    cli()
