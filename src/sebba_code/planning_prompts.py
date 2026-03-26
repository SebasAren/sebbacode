"""Planning prompt templates for draft, critique, and refine stages."""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sebba_code.state import AgentState

MAX_L0_CHARS = 2000
MAX_RULES_CHARS = 1500
MAX_L1_CHARS = 800
MAX_BRIEFING_CHARS = 2000


def _truncate(text: str, max_chars: int, suffix: str = "...") -> str:
    if len(text) <= max_chars:
        return text
    return text[: max_chars - len(suffix)] + suffix


def draft_plan_prompt(state: "AgentState", context: dict | None = None) -> str:
    """Generate the prompt for creating a structured task plan with dependencies."""
    user_request = state.get("user_request", "")
    memory = state.get("memory", {})
    briefing = state.get("briefing", "")

    memory_sections = []

    l0_index = memory.get("l0_index", "")
    if l0_index:
        memory_sections.append(f"# Project Overview\n{_truncate(l0_index, MAX_L0_CHARS)}")

    active_rules = memory.get("active_rules", {})
    if active_rules:
        rules_text = "\n\n".join(f"## {name}\n{content}" for name, content in active_rules.items())
        memory_sections.append(f"# Active Rules (MUST follow)\n{_truncate(rules_text, MAX_RULES_CHARS)}")

    l1_files = memory.get("l1_files", {})
    if l1_files:
        l1_texts = [f"## {name}\n{_truncate(content, MAX_L1_CHARS)}" for name, content in l1_files.items()]
        memory_sections.append("# Relevant Context\n" + "\n\n".join(l1_texts))

    if context:
        if context.get("file_structure"):
            memory_sections.append(f"# File Structure\n{context['file_structure']}")

    rejection_section = ""
    if context and context.get("rejected_plan"):
        rejection_section = f"""# Previous Plan (REJECTED)

The following plan was rejected by the user. Address their feedback.

## Rejected Plan
{context['rejected_plan']}

## Rejection Reason
{context['rejection_reason']}

---

"""

    briefing_section = ""
    if briefing:
        briefing_section = f"# Codebase Briefing\n{_truncate(briefing, MAX_BRIEFING_CHARS)}\n\n"

    memory_context = "\n\n---\n\n".join(memory_sections) if memory_sections else "(No prior context available)"

    prompt = f"""You are creating an execution plan as a DAG of tasks with dependency edges.

## User Request
{user_request}

{rejection_section}{briefing_section}# Memory Context
{memory_context}

---

# Explore Before Planning

**IMPORTANT**: Before creating any subagent tasks, you MUST first run the `explore_codebase` tool to understand the codebase structure, existing patterns, and relevant file locations. Use a focused question like "Where is similar functionality implemented?" or "What patterns exist for [task type]?" — do NOT do a general exploration. Return from the explore tool before proceeding.

---

# Output Format

Generate a JSON object with a "tasks" array. Each task has:
- "id": unique identifier like "task-001", "task-002", etc.
- "description": specific, actionable description starting with an action verb
- "depends_on": array of task IDs that must complete before this task can start (empty array if no dependencies)
- "target_files": array of file paths this task will create or modify

Tasks that don't depend on each other will run in parallel, so design the DAG to maximize parallelism where safe.

Example:
```json
{{
  "tasks": [
    {{"id": "task-001", "description": "Create the database migration for user_sessions table", "depends_on": [], "target_files": ["migrations/001_user_sessions.sql"]}},
    {{"id": "task-002", "description": "Add session management types to the auth module", "depends_on": [], "target_files": ["src/auth/types.ts"]}},
    {{"id": "task-003", "description": "Implement session CRUD operations using the new table and types", "depends_on": ["task-001", "task-002"], "target_files": ["src/auth/sessions.ts"]}},
    {{"id": "task-004", "description": "Write integration tests for session management", "depends_on": ["task-003"], "target_files": ["tests/auth/sessions.test.ts"]}}
  ]
}}
```

# Guidelines

1. Keep tasks focused on the user's request — avoid scope creep
2. Use concrete, specific language — "Add X to Y" not "Improve Y"
3. Ensure proper dependency ordering — foundation tasks before dependent tasks
4. Maximize parallelism — tasks that touch different files and don't depend on each other should have no dependency edge
5. Limit to 3-8 tasks — prefer fewer, larger tasks over many small ones
6. Each task should be completable in one session (1-4 hours)
7. Reference existing patterns in the codebase where applicable
8. IMPORTANT: Use actual file paths from the codebase briefing above. Do NOT invent paths — find where similar code already lives and place new files alongside it.

Generate your task plan JSON now.
"""
    return prompt
