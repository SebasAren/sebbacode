"""Initializes agent directory structure."""

from sebba_code.constants import get_agent_dir


def init_agent_structure() -> None:
    """Create the .agent/ directory structure with empty templates.
    
    Creates the full agent directory tree:
    .agent/
        memory/
            context/      - conversation context and state snapshots
            knowledge/    - persistent knowledge and learnings
            history/      - session and execution history
            scratch/      - temporary working files
        rules/            - agent rules and guidelines
        branches/         - branch state snapshots
        sessions/         - session logs
    """
    agent_dir = get_agent_dir()

    # Base directories
    dirs = [
        agent_dir / "memory",
        agent_dir / "rules",
        agent_dir / "branches",
        agent_dir / "sessions",
    ]
    for d in dirs:
        d.mkdir(parents=True, exist_ok=True)

    # Memory subdirectories
    memory_subdirs = [
        agent_dir / "memory" / "context",
        agent_dir / "memory" / "knowledge",
        agent_dir / "memory" / "history",
        agent_dir / "memory" / "scratch",
    ]
    for d in memory_subdirs:
        d.mkdir(parents=True, exist_ok=True)

    # Create empty index
    index = agent_dir / "memory" / "_index.md"
    if not index.exists():
        index.write_text("# Agent Memory Index\n\n(Empty — will be populated on first run)\n")

    # Create default config
    config = agent_dir / "config.yaml"
    if not config.exists():
        config.write_text("""llm:
  model: "claude-sonnet-4-6"
  # model_provider: "anthropic"
  # base_url: ""
  # api_key: ""
  cheap_model: "claude-haiku-4-5-20251001"

loading:
  l0_max_tokens: 500
  l1_max_tokens: 2000
  l2_max_tokens: 4000
  max_total_context: 12000

explorer:
  bootstrap_on_empty: true

execution:
  max_parallel_workers: 3
  max_tool_calls_per_task: 50

planning:
  max_iterations: 3
  auto_approve: false
""")
