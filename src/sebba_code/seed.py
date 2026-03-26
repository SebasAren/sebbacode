"""Initializes agent directory structure and roadmaps from issues."""

from pathlib import Path

from sebba_code.constants import get_agent_dir
from sebba_code.llm import get_llm


def seed_roadmap_from_issue(
    issue_title: str,
    issue_description: str,
    labels: str = "",
    milestone: str = "",
    use_refine: bool = False,
) -> None:
    """Generate a roadmap from an issue description.

    Args:
        issue_title: Title of the issue/task
        issue_description: Detailed description of what needs to be done
        labels: Optional labels from the issue
        milestone: Optional milestone context
        use_refine: If True, use the planning loop for iterative refinement.
                    If False, use single LLM call (backward compatible default).
    """
    if use_refine:
        _seed_with_planning_loop(issue_title, issue_description, labels, milestone)
    else:
        _seed_with_single_call(issue_title, issue_description, labels, milestone)


def _seed_with_single_call(
    issue_title: str,
    issue_description: str,
    labels: str = "",
    milestone: str = "",
) -> None:
    """Original one-shot LLM call implementation."""
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
- Decisions Made: (start empty)
- Constraints: non-functional requirements, things to preserve

Keep todos concrete and specific.
"""

    llm = get_llm()
    response = llm.invoke(seed_prompt)

    _write_roadmap(response.content)


def _seed_with_planning_loop(
    issue_title: str,
    issue_description: str,
    labels: str = "",
    milestone: str = "",
) -> None:
    """Use the planning loop for iterative roadmap refinement.

    This invokes the planning nodes directly (draft → critique → refine → ...)
    until planning is complete, then writes the final roadmap.
    """
    from sebba_code.config import load_config
    from sebba_code.nodes.planning import (
        critique_roadmap,
        draft_roadmap,
        is_planning_complete,
        refine_roadmap,
        write_roadmap,
    )

    # Build user request from issue components
    user_request = _build_user_request(issue_title, issue_description, labels, milestone)

    # Get config for planning settings
    agent_dir = get_agent_dir()
    config = load_config(agent_dir)
    max_iterations = config.planning.max_iterations
    planning_model = config.planning.model if config.planning.model else None

    # Build configurable dict for planning nodes
    configurable = {"planning_max_iterations": max_iterations}
    if planning_model:
        configurable["planning_model"] = planning_model

    # Initialize planning state (mirrors what graph would build)
    state = {
        # User request
        "user_request": user_request,
        # Planning state
        "draft_roadmap": "",
        "planning_messages": [],
        "planning_iteration": 0,
        "planning_complete": False,
        # Memory context (empty for seed, nodes will handle)
        "memory": {
            "l0_index": "",
            "l1_files": {},
            "l2_files": {},
            "active_rules": {},
            "session_history": "",
        },
        # Other state fields (needed by nodes)
        "roadmap": "",
        "briefing": "",
        "target_files": [],
    }

    # Run the planning loop: draft → critique → [complete?] → write or refine
    while True:
        # Draft phase
        draft_result = draft_roadmap(state, configurable)
        state.update(draft_result)

        # Critique phase
        critique_result = critique_roadmap(state, configurable)
        state.update(critique_result)

        # Check if planning is complete
        complete = is_planning_complete(state)
        if complete == "yes":
            # Write the final roadmap
            write_roadmap(state)
            return

        # Refine phase - loop back to critique
        refine_result = refine_roadmap(state, configurable)
        state.update(refine_result)


def _build_user_request(
    issue_title: str,
    issue_description: str,
    labels: str = "",
    milestone: str = "",
) -> str:
    """Build a unified user request string from issue components."""
    parts = [f"Issue: {issue_title}"]

    if issue_description:
        parts.append(f"\nDescription: {issue_description}")

    if labels:
        parts.append(f"\nLabels: {labels}")

    if milestone:
        parts.append(f"\nMilestone: {milestone}")

    return "\n".join(parts)


def _write_roadmap(content: str) -> None:
    """Write roadmap content to .agent/roadmap.md."""
    agent_dir = get_agent_dir()
    agent_dir.mkdir(parents=True, exist_ok=True)
    (agent_dir / "roadmap.md").write_text(content)


def init_agent_structure() -> None:
    """Create the .agent/ directory structure with empty templates."""
    agent_dir = get_agent_dir()

    dirs = [
        agent_dir / "memory",
        agent_dir / "rules",
        agent_dir / "branches",
        agent_dir / "roadmaps" / "archive",
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

explorer:
  bootstrap_on_empty: true
  validate_new_roadmaps: true
  recon_before_todo: true

execution:
  max_todos_per_session: 5
  max_tool_calls_per_todo: 50

planning:
  max_iterations: 3
  # model: ""              # uncomment to override (empty = use default LLM)
  auto_approve: false
""")
