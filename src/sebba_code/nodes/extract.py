"""Implements post-execution finalization and session extraction nodes."""

import logging

from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

from sebba_code.constants import DEFAULT_MAX_TODOS, DEBUG_PROMPTS, get_agent_dir
from sebba_code.helpers.files import summarize_memory_files, summarize_rules
from sebba_code.helpers.memory_ops import (
    append_or_create,
    apply_index_updates,
    apply_memory_updates,
    apply_new_rules,
    format_session_from_summaries,
)
from sebba_code.helpers.parsing import parse_json
from sebba_code.llm import get_cheap_llm, get_llm
from sebba_code.state import AgentState, TodoSummary


logger = logging.getLogger("sebba_code")


def _format_messages_for_summary(messages: list, max_chars: int = 4000) -> str:
    """Format recent messages into a compact text for LLM summarization."""
    parts: list[str] = []
    total = 0
    for msg in reversed(messages):
        if isinstance(msg, AIMessage):
            if msg.tool_calls:
                calls = ", ".join(tc["name"] for tc in msg.tool_calls)
                line = f"AI: [called: {calls}]"
            else:
                line = f"AI: {(msg.content or '')[:200]}"
        elif isinstance(msg, ToolMessage):
            result = str(msg.content)[:150].replace("\n", " ")
            line = f"Tool({msg.name}): {result}"
        elif isinstance(msg, HumanMessage):
            line = f"Human: {str(msg.content)[:150]}"
        else:
            continue
        total += len(line)
        if total > max_chars:
            break
        parts.append(line)
    parts.reverse()
    return "\n".join(parts)


def finalize_todo(state: AgentState) -> dict:
    """Mark the current todo as done and create a summary in state.

    Runs after execute_todo to ensure progress is always recorded,
    regardless of whether the LLM called the tools itself.
    """
    current_todo = state.get("current_todo")
    if not current_todo:
        return {}

    todo_text = current_todo["text"]
    agent_dir = get_agent_dir()
    logger.info("Finalizing todo: %s", todo_text)

    # --- A) Auto-mark todo done in roadmap (idempotent) ---
    roadmap_path = agent_dir / "roadmap.md"
    roadmap_content = ""
    if roadmap_path.exists():
        content = roadmap_path.read_text()
        if f"- [x] ~~{todo_text}~~" not in content:
            old = f"- [ ] {todo_text}"
            if old in content:
                content = content.replace(old, f"- [x] ~~{todo_text}~~", 1)
                roadmap_path.write_text(content)
                logger.info("Auto-marked todo done: %s", todo_text)
        roadmap_content = roadmap_path.read_text()

    # --- B) Create TodoSummary via cheap LLM ---
    summary_text = todo_text
    what_i_did = f"- Completed: {todo_text}"
    decisions_made = ""
    files_touched = ""

    messages = state.get("messages", [])
    formatted = _format_messages_for_summary(messages)

    if formatted:
        try:
            prompt = (
                f"Summarize this coding session for a progress log.\n\n"
                f"Todo: {todo_text}\n\n"
                f"Conversation:\n{formatted}\n\n"
                f"Respond with JSON:\n"
                f'{{"summary": "one-line summary",'
                f' "what_i_did": "bullet list of actions",'
                f' "decisions_made": "choices and rationale (or empty string)",'
                f' "files_touched": "files modified (or empty string)"}}'
            )
            response = get_cheap_llm().invoke(prompt)
            result = parse_json(response.content)
            if result:
                summary_text = result.get("summary", summary_text)
                what_i_did = result.get("what_i_did", what_i_did)
                decisions_made = result.get("decisions_made", "")
                files_touched = result.get("files_touched", "")
        except Exception:
            logger.warning("Auto-commit summary failed, using fallback", exc_info=True)

    new_summary: TodoSummary = {
        "todo_text": todo_text,
        "summary": summary_text,
        "what_i_did": what_i_did,
        "decisions_made": decisions_made,
        "files_touched": files_touched,
    }

    existing_summaries = list(state.get("todo_summaries", []))
    existing_completed = list(state.get("todos_completed_this_session", []))

    return {
        "todo_summaries": existing_summaries + [new_summary],
        "todos_completed_this_session": existing_completed + [todo_text],
        "roadmap": roadmap_content,
    }


def extract_session(state: AgentState) -> dict:
    """Read todo summaries from state, distill into lasting memory."""
    logger.info("Extracting session activity into lasting memory")
    agent_dir = get_agent_dir()
    summaries = state.get("todo_summaries", [])

    if not summaries:
        return {}

    # Format summaries into text for the extraction LLM
    parts = []
    for i, s in enumerate(summaries, 1):
        part = f"## Todo {i}: {s['summary']}\n\n### What was done\n{s['what_i_did']}\n"
        if s.get("decisions_made"):
            part += f"\n### Decisions Made\n{s['decisions_made']}\n"
        if s.get("files_touched"):
            part += f"\n### Files Touched\n{s['files_touched']}\n"
        parts.append(part)
    combined = "\n\n---\n\n".join(parts)

    memory_inventory = summarize_memory_files(agent_dir / "memory")
    rules_inventory = summarize_rules(agent_dir / "rules")

    extraction_prompt = f"""Read this session activity and extract lasting knowledge.

## Session Activity
{combined}

## Current Memory Index
{state["memory"]["l0_index"]}

## Existing Memory Files
{memory_inventory}

## Existing Rules
{rules_inventory}

## Todos Completed
{chr(10).join(f'- {t}' for t in state.get('todos_completed_this_session', []))}

Extract JSON:
{{
  "memory_updates": [
    {{"file": "architecture/auth-system.md", "action": "create|append|replace_section", "section": "optional", "content": "..."}}
  ],
  "index_updates": [
    {{"old_line": "existing line or null", "new_line": "updated summary"}}
  ],
  "new_rules": [
    {{"file": "rules/auth-middleware.md", "paths": ["apps/api/src/middleware/**"], "content": "rule text"}}
  ]
}}

Memory rules:
- PREFER updating existing files over creating new ones
- Use "append" to add a new section to an existing file on the same topic
- Use "replace_section" to update a specific section in an existing file
- Use "create" ONLY when no existing file covers the topic
- Check the file list above — do NOT create near-duplicates of existing files
- L1 files (architecture.md, conventions.md) are broad overviews — update them when you learn something that applies project-wide
- L2 files (in subdirectories) are for deep-dive, topic-specific knowledge
- Only extract genuinely NEW knowledge not already in memory
- Decisions from exploration branches are especially valuable
- Keep index lines under 100 characters
- Empty lists if nothing new was learned

Rules vs memory:
- Memory stores knowledge (facts, architecture, patterns)
- Rules store INSTRUCTIONS that are injected into the system prompt when working on matching files
- Create a rule when you discover a constraint, convention, or gotcha that applies to specific file paths
- Examples: "always use X pattern in tests/**", "never import Y in src/api/**", "files in migrations/ must be idempotent"
- Rules need a "paths" array of glob patterns (or null for global rules)
- Check existing rules above — do NOT duplicate them
"""

    llm = get_llm()
    if DEBUG_PROMPTS:
        logger.debug("── extraction prompt (%d chars) ──\n%s", len(extraction_prompt), extraction_prompt[:2000])
    response = llm.invoke(extraction_prompt)
    updates = parse_json(response.content)

    apply_memory_updates(updates.get("memory_updates", []))
    apply_index_updates(updates.get("index_updates", []))
    apply_new_rules(updates.get("new_rules", []))

    # Write session summary
    from datetime import date

    session_file = agent_dir / "sessions" / f"{date.today().isoformat()}.md"
    append_or_create(
        session_file, format_session_from_summaries(summaries, updates)
    )

    # Clear summaries for next loop iteration
    return {"todo_summaries": []}


def should_continue(state: AgentState) -> str:
    logger.info("Checking if session should continue")
    completed = len(state.get("todos_completed_this_session", []))
    max_todos = state.get("max_todos")
    if max_todos is None:
        max_todos = DEFAULT_MAX_TODOS
    if completed >= max_todos:
        return "no"
    if state.get("current_todo") is not None:
        return "yes"
    return "no"
