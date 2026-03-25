"""Initializes agent directory structure and roadmaps from issues."""

from pathlib import Path

from sebba_code.constants import get_agent_dir
from sebba_code.llm import get_llm


def seed_roadmap_from_issue(issue_title: str, issue_description: str, labels: str = "", milestone: str = "") -> None:
    """Generate a roadmap main.md from an issue description."""
    agent_dir = get_agent_dir()

    seed_prompt = f"""Decompose this issue into an agent roadmap.

Issue: {issue_title}
{issue_description}

Labels: {labels}
Milestone: {milestone}

Generate a markdown document with these sections:
- Goal: one paragraph
- Context: where this came from, current state of the codebase
- Todos: ordered, actionable steps (each completable in one session)
- Target Files: best guess at files to create or modify
- Active Branches: (start empty)
- Decisions Made: (start empty)
- Constraints: non-functional requirements, things to preserve

Keep todos concrete and specific.
"""

    llm = get_llm()
    response = llm.invoke(seed_prompt)

    gcc_dir = agent_dir / "gcc"
    gcc_dir.mkdir(parents=True, exist_ok=True)
    (gcc_dir / "main.md").write_text(response.content)
    (gcc_dir / "commits").mkdir(exist_ok=True)
    (gcc_dir / "branches").mkdir(exist_ok=True)


def init_agent_structure() -> None:
    """Create the .agent/ directory structure with empty templates."""
    agent_dir = get_agent_dir()

    dirs = [
        agent_dir / "memory",
        agent_dir / "rules",
        agent_dir / "gcc",
        agent_dir / "gcc" / "commits",
        agent_dir / "gcc" / "branches",
        agent_dir / "sessions",
    ]
    for d in dirs:
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
  # model_provider: "anthropic"    # auto-detected from model name if omitted
  # base_url: ""                   # custom API endpoint (e.g. for proxies or local models)
  # api_key: ""                    # override ANTHROPIC_API_KEY / OPENAI_API_KEY env var
  cheap_model: "claude-haiku-4-5-20251001"
  # cheap_model_provider: ""
  # cheap_base_url: ""
  # cheap_api_key: ""

loading:
  l0_max_tokens: 500
  l1_max_tokens: 2000
  l2_max_tokens: 4000
  max_total_context: 12000

gcc:
  max_main_md_lines: 60
  k: 1
  archive_on_complete: true

explorer:
  bootstrap_on_empty: true
  validate_new_roadmaps: true
  recon_before_todo: true

execution:
  max_todos_per_session: 5
  max_tool_calls_per_todo: 50
""")
