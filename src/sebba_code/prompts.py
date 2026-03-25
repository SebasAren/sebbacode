"""System prompt assembly from agent state for LLM context."""

from sebba_code.state import AgentState


def build_system_prompt(state: AgentState) -> str:
    """Assemble the system prompt from current state."""
    memory = state["memory"]
    todo = state.get("current_todo")
    sections = []

    if todo:
        sections.append(
            f"# Current Objective\n"
            f"Working on: **{todo['text']}**\n\n"
            f"Full roadmap:\n{state['roadmap']}"
        )

    if state.get("briefing"):
        sections.append(f"# Codebase Briefing\n{state['briefing']}")

    sections.append(f"# Project Context\n{memory['l0_index']}")

    if memory["active_rules"]:
        rules = "\n\n".join(
            f"## {n}\n{c}" for n, c in memory["active_rules"].items()
        )
        sections.append(f"# Rules (MUST follow)\n{rules}")

    for n, c in memory.get("l1_files", {}).items():
        sections.append(f"# Memory: {n}\n{c}")
    for n, c in memory.get("l2_files", {}).items():
        sections.append(f"# Detail: {n}\n{c}")

    if memory.get("session_history"):
        sections.append(f"# Previous Progress\n{memory['session_history']}")

    return "\n\n---\n\n".join(sections)
