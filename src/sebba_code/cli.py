"""Command-line interface commands for the agent."""

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


@cli.command()
def init():
    """Create the .agent/ directory structure."""
    from sebba_code.seed import init_agent_structure

    init_agent_structure()
    click.echo(f"Initialized {get_agent_dir()}/")


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

    # Run graph — will pause at human_approval interrupt
    for event in graph.stream(initial_state, config=config, stream_mode="updates"):
        elapsed = time.monotonic() - start_time
        for node_name, node_output in event.items():
            if node_name == "plan_draft":
                click.echo(f"[{elapsed:.1f}s] Planning...")
            elif node_name == "plan_critique":
                click.echo(f"[{elapsed:.1f}s] Validating plan...")
            elif node_name == "build_dag":
                tasks = node_output.get("tasks", {})
                click.echo(f"[{elapsed:.1f}s] Built DAG with {len(tasks)} tasks")
            elif node_name == "human_approval":
                # Interrupt happened — show plan and get user input
                pass
            elif node_name == "dispatch_tasks":
                click.echo(f"[{elapsed:.1f}s] Dispatching tasks...")
            elif node_name == "task_worker":
                click.echo(f"[{elapsed:.1f}s] Task worker completed")
            elif node_name == "collect_results":
                click.echo(f"[{elapsed:.1f}s] Collecting results...")
                if "tasks" in node_output:
                    click.echo(format_dag(node_output["tasks"]))
            elif node_name == "extract_session":
                click.echo(f"[{elapsed:.1f}s] Extracting session memory...")

    # Check if we're paused at an interrupt
    graph_state = graph.get_state(config)
    while graph_state.next:
        if "human_approval" in graph_state.next:
            # Show the plan
            tasks = graph_state.values.get("tasks", {})
            click.echo("\n=== Execution Plan ===\n")
            for tid, task in tasks.items():
                deps = ", ".join(task["depends_on"]) if task["depends_on"] else "none"
                files = ", ".join(task["target_files"]) if task["target_files"] else "none"
                click.echo(f"  {tid}: {task['description']}")
                click.echo(f"    deps: {deps} | files: {files}")
            click.echo("")

            if auto_approve:
                response = "yes"
                click.echo("Auto-approving plan...")
            else:
                response = click.prompt(
                    "Approve? (yes/no or feedback)",
                    default="yes",
                )

            # Resume with user response
            for event in graph.stream(Command(resume=response), config=config, stream_mode="updates"):
                elapsed = time.monotonic() - start_time
                for node_name, node_output in event.items():
                    if node_name == "plan_draft":
                        click.echo(f"[{elapsed:.1f}s] Re-planning with feedback...")
                    elif node_name == "dispatch_tasks":
                        click.echo(f"[{elapsed:.1f}s] Dispatching tasks...")
                    elif node_name == "task_worker":
                        click.echo(f"[{elapsed:.1f}s] Task worker completed")
                    elif node_name == "collect_results":
                        click.echo(f"[{elapsed:.1f}s] Collecting results...")
                        if "tasks" in node_output:
                            click.echo(format_dag(node_output["tasks"]))
                    elif node_name == "extract_session":
                        click.echo(f"[{elapsed:.1f}s] Extracting session memory...")

            # Check for more interrupts (re-planning loop)
            graph_state = graph.get_state(config)
        else:
            break

    # Report results
    final_state = graph.get_state(config)
    completed = final_state.values.get("tasks_completed_this_session", [])
    if completed:
        elapsed = time.monotonic() - start_time
        click.echo(f"\n[{elapsed:.1f}s] Completed {len(completed)} tasks:")
        for tid in completed:
            click.echo(f"  - {tid}")
    else:
        click.echo("\nNo tasks completed this session.")


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
