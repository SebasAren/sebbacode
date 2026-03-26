"""Command-line interface commands for the agent."""

import argparse
import logging
from pathlib import Path

import click

from sebba_code.config import load_config
from sebba_code.constants import get_agent_dir, init_agent_dir, set_debug_prompts

logger = logging.getLogger("sebba_code")

STATUS_ICONS = {"done": "\u2713", "running": "\u25b6", "pending": "\u00b7", "blocked": "\u2717"}


def format_dag(tasks: dict) -> str:
    """Format the task DAG as a compact status table."""
    lines = []
    for tid, task in tasks.items():
        icon = STATUS_ICONS.get(task["status"], "?")
        deps = ", ".join(task["depends_on"]) if task["depends_on"] else ""
        dep_str = f"  (deps: {deps})" if deps else ""
        lines.append(f"  {icon} {tid}: {task['description']}{dep_str}")
    return "\n".join(lines)


@click.group()
@click.option("--agent-dir", default=".agent", help="Path to .agent directory")
def cli(agent_dir: str):
    """LangGraph coding agent with tiered memory."""
    init_agent_dir(Path(agent_dir))


def _has_source_files(project_path: Path) -> bool:
    """Check if the project directory contains source files worth exploring.
    
    Looks for common source file patterns to determine if exploration would be useful.
    Excludes the .agent directory to avoid detecting files created during init.
    """
    source_extensions = {
        ".py", ".js", ".ts", ".jsx", ".tsx", ".java", ".go", ".rs", ".c", ".cpp",
        ".h", ".hpp", ".cs", ".rb", ".php", ".swift", ".kt", ".scala", ".lua",
        ".sh", ".bash", ".zsh", ".yaml", ".yml", ".json", ".toml", ".xml",
        ".md", ".rst", ".txt", ".sql",
    }
    ignore_dirs = {".git", ".venv", "venv", "node_modules", "__pycache__", ".pytest_cache", ".agent"}
    
    for item in project_path.rglob("*"):
        if item.is_file():
            # Check if in ignored directory
            if any(ignored in item.parts for ignored in ignore_dirs):
                continue
            # Check extension
            if item.suffix in source_extensions or item.name in {"Makefile", "Dockerfile", "Procfile"}:
                return True
    return False


def _explore_project_structure(project_path: Path, agent_dir: Path) -> bool:
    """Explore the project structure and save exploration results.
    
    Returns True if exploration was performed, False if skipped.
    """
    from sebba_code.tools.explore_agent import explore_codebase
    
    try:
        exploration_question = (
            "Analyze this project's structure. Identify:\n"
            "1. Main source directories and their purposes\n"
            "2. Configuration files and their locations\n"
            "3. Key entry points and modules\n"
            "4. Testing setup and locations\n"
            "5. Any notable patterns or architectural choices\n\n"
            "Provide a concise summary of how the codebase is organized."
        )
        
        click.echo("  Exploring project structure...")
        exploration_result = explore_codebase(exploration_question)
        
        # Write exploration results to memory/knowledge/
        exploration_file = agent_dir / "memory" / "knowledge" / "project_structure.md"
        exploration_content = f"""# Project Structure Exploration

Explored at: {Path.cwd()}

## Question
{exploration_question}

## Findings
{exploration_result}
"""
        exploration_file.write_text(exploration_content)
        
        return True
        
    except Exception as e:
        logger.warning("Exploration failed: %s", e)
        click.echo(f"  Warning: Could not explore project structure: {e}")
        return False


def _init_with_path(project_path: Path, skip_exploration: bool = False) -> None:
    """Initialize agent directory structure at the given project path.
    
    This is an internal helper that handles the actual initialization logic
    using argparse-style Path resolution for the project_path argument.
    
    Args:
        project_path: Path to the project directory
        skip_exploration: If True, skip the codebase exploration step
    """
    from sebba_code.seed import init_agent_structure

    # Resolve the project path (default to cwd if not provided)
    resolved_path = project_path.resolve() if project_path else Path.cwd()
    
    # Change to the project directory to initialize there
    original_cwd = Path.cwd()
    try:
        import os
        os.chdir(resolved_path)
        
        # Initialize the agent structure
        init_agent_structure()
        
        # Get the agent dir that was created
        agent_dir = get_agent_dir()
        click.echo(f"Initialized {agent_dir}/ at {resolved_path}/")
        
        # Explore project structure if not skipped and project has source files
        if not skip_exploration:
            if _has_source_files(resolved_path):
                # Configure LLM first (required for exploration)
                _configure_llm_from_config()
                _explore_project_structure(resolved_path, agent_dir)
            else:
                click.echo("  Skipping exploration (no source files detected)")
                
    finally:
        os.chdir(original_cwd)


@cli.command()
@click.argument("project_path", required=False, default=None, type=click.Path(exists=False))
@click.option("--skip-exploration", is_flag=True, help="Skip codebase exploration during init")
def init(project_path: str, skip_exploration: bool):
    """Create the .agent/ directory structure.
    
    PROJECT_PATH is an optional path to the project directory.
    Defaults to the current working directory if not specified.
    
    By default, this command explores the project structure using an LLM
    and saves the findings to .agent/memory/knowledge/project_structure.md.
    Use --skip-exploration to skip this step.
    """
    # Use argparse-style resolution: default to cwd if not provided
    if project_path is None:
        project_path_obj = Path.cwd()
    else:
        project_path_obj = Path(project_path)
    
    _init_with_path(project_path_obj, skip_exploration=skip_exploration)


def _configure_llm_from_config():
    """Load config and configure LLM instances."""
    from sebba_code.llm import configure_llm

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


@cli.command()
def status():
    """Print a summary of the current agent state."""
    from sebba_code.helpers.files import list_available_files

    agent_dir = get_agent_dir()
    memory_dir = agent_dir / "memory"

    click.echo("=== Agent Status ===\n")

    # Memory files
    click.echo("Memory Files (.agent/memory/):")
    if memory_dir.exists():
        memory_files = sorted(
            f.relative_to(memory_dir)
            for f in memory_dir.rglob("*")
            if f.is_file()
        )
        if memory_files:
            for f in memory_files:
                click.echo(f"  {f}")
        else:
            click.echo("  (no memory files)")
    else:
        click.echo("  (no memory directory)")

    # Sessions
    session_dir = agent_dir / "sessions"
    if session_dir.exists():
        sessions = sorted(session_dir.glob("*.md"))
        if sessions:
            click.echo(f"\nSessions ({len(sessions)}):")
            for s in sessions[-5:]:
                click.echo(f"  {s.name}")


@cli.command()
@click.argument("request")
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose logging")
@click.option("--debug-prompts", is_flag=True, help="Log prompts and message summaries")
@click.option("--auto-approve", is_flag=True, help="Skip human approval step")
def run(request: str, verbose: bool, debug_prompts: bool, auto_approve: bool):
    """Plan and execute tasks for the given request."""
    import time

    from langgraph.checkpoint.memory import MemorySaver
    from langgraph.types import Command

    from sebba_code.display import RichDisplay

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

    checkpointer = MemorySaver()
    graph = build_agent_graph(checkpointer=checkpointer)

    config = {"configurable": {"thread_id": "main"}}
    initial_state = {
        "messages": [],
        "user_request": request,
    }

    logger.info("Starting agent for: %s", request[:80])
    start_time = time.monotonic()

    stream_kwargs = dict(
        config=config,
        stream_mode=["updates", "messages"],
        subgraphs=True,
    )

    with RichDisplay(verbose=verbose) as display:
        # Run graph — will pause at human_approval interrupt
        for chunk in graph.stream(initial_state, **stream_kwargs):
            display.handle_stream_event(chunk)

        # Check if we're paused at an interrupt
        graph_state = graph.get_state(config)
        while graph_state.next:
            if "human_approval" in graph_state.next:
                display.pause()

                # Show the plan
                tasks = graph_state.values.get("tasks", {})
                display.show_plan(tasks)

                if auto_approve:
                    response = "yes"
                    display.console.print("[bold green]Auto-approving plan...[/]")
                else:
                    response = click.prompt(
                        "Approve? (yes/no or feedback)",
                        default="yes",
                    )

                display.resume()

                # Resume with user response
                for chunk in graph.stream(Command(resume=response), **stream_kwargs):
                    display.handle_stream_event(chunk)

                # Check for more interrupts (re-planning loop)
                graph_state = graph.get_state(config)
            else:
                break

    # Report results (after Live context exits)
    final_state = graph.get_state(config)
    completed = final_state.values.get("tasks_completed_this_session", [])
    elapsed = time.monotonic() - start_time
    display.show_final_report(completed, elapsed)


@cli.command()
@click.argument("request")
@click.option("--iterations", "-i", type=int, default=None, help="Max planning iterations")
def plan(request: str, iterations: int | None):
    """Generate an execution plan without running it.

    Shows the task DAG for review.
    """
    _configure_llm_from_config()

    from sebba_code.seed import init_agent_structure

    init_agent_structure()
    click.echo(f"Initialized {get_agent_dir()}/")

    from sebba_code.nodes.approval import build_dag
    from sebba_code.nodes.planning import plan_critique, plan_draft

    config = load_config(get_agent_dir())
    max_iterations = iterations or config.planning.max_iterations
    configurable = {"planning_max_iterations": max_iterations}

    state = {
        "user_request": request,
        "draft_plan": "",
        "planning_messages": [],
        "planning_iteration": 0,
        "planning_complete": False,
        "rejection_reason": "",
        "memory": {
            "l0_index": "",
            "l1_files": {},
            "l2_files": {},
            "active_rules": {},
            "session_history": "",
        },
        "briefing": "",
    }

    click.echo("Drafting plan...")
    draft_result = plan_draft(state, configurable)
    state.update(draft_result)

    click.echo("Validating plan...")
    critique_result = plan_critique(state, configurable)
    state.update(critique_result)

    # Build DAG for display
    dag_result = build_dag(state)
    tasks = dag_result.get("tasks", {})

    click.echo(f"\n=== Task DAG ({len(tasks)} tasks) ===\n")
    for tid, task in tasks.items():
        deps = ", ".join(task["depends_on"]) if task["depends_on"] else "none"
        files = ", ".join(task["target_files"]) if task["target_files"] else "none"
        click.echo(f"  {tid}: {task['description']}")
        click.echo(f"    deps: {deps} | files: {files}")

    click.echo(f"\nRaw plan:\n{state['draft_plan']}")


@cli.command()
@click.argument("title")
@click.option("--description", "-d", default="", help="Issue description")
@click.option("--labels", "-l", default="", help="Issue labels")
def seed(title: str, description: str, labels: str):
    """Seed agent memory from an issue description."""
    _configure_llm_from_config()

    from sebba_code.seed import init_agent_structure

    init_agent_structure()
    click.echo(f"Initialized {get_agent_dir()}/")
    click.echo("Use 'sebba-code run' with your request to plan and execute tasks.")


if __name__ == "__main__":
    cli()
