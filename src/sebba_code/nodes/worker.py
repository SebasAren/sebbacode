"""Task worker subgraph — executes a single task with its own message history."""

import logging
import subprocess
from pathlib import Path

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langgraph.graph import END, StateGraph
from langgraph.prebuilt import ToolNode, tools_condition

from sebba_code.constants import DEBUG_PROMPTS, get_agent_dir
from sebba_code.helpers.files import is_relevant, list_available_files, summarize_memory_files, summarize_rules
from sebba_code.helpers.markdown import summarise_file
from sebba_code.helpers.memory_ops import format_session_from_summaries
from sebba_code.helpers.parsing import format_dict, parse_json, parse_json_list
from sebba_code.llm import get_cheap_llm, get_llm
from sebba_code.state import TaskResult, WorkerState
from sebba_code.tools import get_worker_tools

logger = logging.getLogger("sebba_code")
debug_logger = logging.getLogger("sebba_code.debug")


def worker_recon(state: WorkerState) -> dict:
    """Per-task reconnaissance — build a briefing for the executor."""
    task = state["task"]
    target_files = state.get("target_files", [])
    logger.info("worker_recon: building briefing for task %s", task["id"])

    file_contents = {}
    for f in target_files:
        path = Path(f)
        if path.exists():
            content = path.read_text()
            if len(content) > 3000:
                file_contents[f] = summarise_file(f, content)
            else:
                file_contents[f] = content
        else:
            file_contents[f] = "(does not exist yet)"

    # Trace imports one level deep
    dependency_map = {}
    for f in target_files:
        if Path(f).exists() and f.endswith((".ts", ".js", ".tsx", ".jsx", ".py")):
            result = subprocess.run(
                ["grep", "-E", r"^(import|export.*from|from .* import)", f],
                capture_output=True, text=True,
            )
            if result.stdout.strip():
                dependency_map[f] = result.stdout.strip()

    # Find related test files
    test_files = {}
    for f in target_files:
        stem = Path(f).stem
        for pattern in [f"**/{stem}.test.ts", f"**/{stem}.spec.ts", f"**/{stem}_test.py", f"**/test_{stem}.py"]:
            for test_file in Path(".").glob(pattern):
                test_files[str(test_file)] = test_file.read_text()[:1000]

    # Recent git history
    git_history = ""
    for f in target_files[:5]:
        if Path(f).exists():
            log = subprocess.run(
                ["git", "log", "--oneline", "-5", "--", f],
                capture_output=True, text=True,
            ).stdout
            if log:
                git_history += f"\n### {f}\n{log}"

    recon_prompt = f"""Build a briefing for this coding task.

## Task: {task["description"]}

## Target Files
{format_dict(file_contents)}

## Dependencies (imports)
{format_dict(dependency_map)}

## Related Tests
{test_files if test_files else "None found."}

## Recent Git History
{git_history or "No recent changes."}

Write a concise, actionable briefing covering:
1. Current State — what exists, what needs creating
2. Dependencies — what this touches beyond target files
3. Patterns to Follow — code patterns from existing files
4. Existing Tests — what's covered, what's missing
5. Risks — things that could go wrong
"""

    llm = get_llm()
    response = llm.invoke(recon_prompt)
    return {"briefing": response.content}


def worker_match_rules(state: WorkerState) -> dict:
    """Load path-scoped rules matching the target files."""
    from fnmatch import fnmatch
    from sebba_code.helpers.rules_ops import find_nearest_agent_dir, parse_path_frontmatter, strip_frontmatter

    agent_dir = get_agent_dir()
    target_files = state.get("target_files", [])
    memory = state["memory"]
    active_rules = {}

    rule_dirs = [agent_dir / "rules"]
    seen = set()
    for target_file in target_files:
        nearest = find_nearest_agent_dir(target_file)
        rd = nearest / "rules"
        if rd.exists() and str(rd) not in seen:
            seen.add(str(rd))
            rule_dirs.append(rd)

    for rules_dir in rule_dirs:
        if not rules_dir.exists():
            continue
        for rule_file in rules_dir.glob("**/*.md"):
            content = rule_file.read_text()
            paths = parse_path_frontmatter(content)
            if paths is None:
                active_rules[rule_file.stem] = strip_frontmatter(content)
            elif any(fnmatch(f, p) for p in paths for f in target_files):
                active_rules[rule_file.stem] = strip_frontmatter(content)

    return {"memory": {**memory, "active_rules": active_rules}}


def worker_deepen_context(state: WorkerState) -> dict:
    """LLM picks relevant L1/L2 memory for this task."""
    agent_dir = get_agent_dir()
    memory = state["memory"]
    task = state["task"]

    retrieval_prompt = f"""You are preparing context for a coding task.

Current task: {task["description"]}
Target files: {state.get("target_files", [])}

Memory index (L0):
{memory["l0_index"]}

Available memory files (L1 top-level, L2 in subdirs):
{list_available_files(agent_dir / "memory", depth=2)}

Return a JSON list of relative paths to load. Be selective.
"""

    llm = get_llm()
    response = llm.invoke(retrieval_prompt)
    requested = parse_json_list(response.content)

    l1_files = {}
    l2_files = {}

    for filepath in requested:
        full_path = agent_dir / "memory" / filepath
        if full_path.exists():
            l1_files[filepath] = full_path.read_text()
            l2_dir = full_path.with_suffix("")
            if l2_dir.is_dir():
                for l2_file in l2_dir.glob("*.md"):
                    if is_relevant(l2_file.stem, task["description"]):
                        key = str(l2_file.relative_to(agent_dir / "memory"))
                        l2_files[key] = l2_file.read_text()

    # Load branch context if on a feature branch
    session_history = ""
    branch = state.get("working_branch", "main")
    branch_dir = agent_dir / "branches" / branch
    if branch_dir.exists() and (branch_dir / "context.md").exists():
        session_history = (branch_dir / "context.md").read_text()

    return {
        "memory": {
            **memory,
            "l1_files": l1_files,
            "l2_files": l2_files,
            "session_history": session_history,
        }
    }


def _build_worker_system_prompt(state: WorkerState) -> str:
    """Assemble the system prompt for a task worker."""
    memory = state["memory"]
    task = state["task"]
    sections = []

    sections.append(
        f"# Current Task\n"
        f"Task ID: **{task['id']}**\n"
        f"Working on: **{task['description']}**\n"
        f"Target files: {', '.join(task['target_files']) if task['target_files'] else 'none specified'}"
    )

    if state.get("briefing"):
        sections.append(f"# Codebase Briefing\n{state['briefing']}")

    sections.append(f"# Project Context\n{memory['l0_index']}")

    if memory["active_rules"]:
        rules = "\n\n".join(f"## {n}\n{c}" for n, c in memory["active_rules"].items())
        sections.append(f"# Rules (MUST follow)\n{rules}")

    for n, c in memory.get("l1_files", {}).items():
        sections.append(f"# Memory: {n}\n{c}")
    for n, c in memory.get("l2_files", {}).items():
        sections.append(f"# Detail: {n}\n{c}")

    if memory.get("session_history"):
        sections.append(f"# Previous Progress\n{memory['session_history']}")

    return "\n\n---\n\n".join(sections)


def _llm_call(state: WorkerState) -> dict:
    """Invoke the LLM with system prompt and tools."""
    logger.info("worker: calling LLM (%d messages)", len(state["messages"]))
    tools = get_worker_tools()
    llm = get_llm().bind_tools(tools)

    system_prompt = _build_worker_system_prompt(state)
    messages = [SystemMessage(content=system_prompt)] + list(state["messages"])

    # Inject a human message if none exists (OpenAI-compatible requirement)
    injected_human_msg = None
    if not any(isinstance(m, HumanMessage) for m in messages):
        task = state["task"]
        briefing = state.get("briefing", "")
        user_msg = f"Execute this task: {task['description']}"
        if briefing:
            user_msg += f"\n\nBriefing:\n{briefing}"
        injected_human_msg = HumanMessage(content=user_msg)
        messages.append(injected_human_msg)

    if DEBUG_PROMPTS:
        debug_logger.debug("── worker system prompt (%d chars) ──\n%s", len(system_prompt), system_prompt[:2000])

    response = llm.invoke(messages)

    if injected_human_msg:
        return {"messages": [injected_human_msg, response]}
    return {"messages": [response]}


def _format_messages_for_summary(messages: list, max_chars: int = 4000) -> str:
    """Format recent messages into compact text for LLM summarization."""
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


def worker_summarize(state: WorkerState) -> dict:
    """Create TaskResult from the worker's conversation."""
    task = state["task"]
    logger.info("Summarizing task %s", task["id"])

    summary_text = task["description"]
    what_i_did = f"- Completed: {task['description']}"
    decisions_made = ""
    files_touched = ""
    dag_mutations: list[dict] = []

    messages = state.get("messages", [])
    formatted = _format_messages_for_summary(messages)

    if formatted:
        try:
            prompt = (
                f"Summarize this coding session for a progress log.\n\n"
                f"Task: {task['description']}\n\n"
                f"Conversation:\n{formatted}\n\n"
                f"Respond with JSON:\n"
                f'{{"summary": "one-line summary",'
                f' "what_i_did": "bullet list of actions",'
                f' "decisions_made": "choices and rationale (or empty string)",'
                f' "files_touched": "comma-separated files modified (or empty string)"}}'
            )
            response = get_cheap_llm().invoke(prompt)
            result = parse_json(response.content)
            if result:
                summary_text = result.get("summary", summary_text)
                what_i_did = result.get("what_i_did", what_i_did)
                decisions_made = result.get("decisions_made", "")
                files_touched = result.get("files_touched", "")
        except Exception:
            logger.warning("Task summary failed, using fallback", exc_info=True)

    task_result = TaskResult(
        task_id=task["id"],
        summary=summary_text,
        what_i_did=what_i_did,
        decisions_made=decisions_made,
        files_touched=files_touched,
        dag_mutations=dag_mutations,
        memory_updates={},
    )

    return {"task_result": task_result}


def worker_extract_memory(state: WorkerState) -> dict:
    """Per-task memory extraction — collects updates for sequential application."""
    task = state["task"]
    task_result = state.get("task_result")
    if not task_result:
        return {}

    agent_dir = get_agent_dir()
    memory = state["memory"]

    memory_inventory = summarize_memory_files(agent_dir / "memory")
    rules_inventory = summarize_rules(agent_dir / "rules")

    extraction_prompt = f"""Read this task result and extract lasting knowledge.

## Task: {task["description"]}

### What was done
{task_result["what_i_did"]}

### Decisions Made
{task_result.get("decisions_made", "none")}

### Files Touched
{task_result.get("files_touched", "none")}

## Current Memory Index
{memory["l0_index"]}

## Existing Memory Files
{memory_inventory}

## Existing Rules
{rules_inventory}

Extract JSON:
{{
  "memory_updates": [
    {{"file": "architecture/example.md", "action": "create|append|replace_section", "section": "optional", "content": "..."}}
  ],
  "index_updates": [
    {{"old_line": "existing line or null", "new_line": "updated summary"}}
  ],
  "new_rules": [
    {{"file": "rules/example.md", "paths": ["glob/**"] , "content": "rule text"}}
  ]
}}

Rules:
- PREFER updating existing files over creating new ones
- Only extract genuinely NEW knowledge not already in memory
- Empty lists if nothing new was learned
- Keep index lines under 100 characters
"""

    try:
        llm = get_cheap_llm()
        response = llm.invoke(extraction_prompt)
        updates = parse_json(response.content)
    except Exception:
        logger.warning("Per-task memory extraction failed", exc_info=True)
        updates = {}

    # Store updates in the task result for sequential application by collect_results
    if task_result:
        task_result["memory_updates"] = updates

    return {"task_result": task_result}


def build_task_worker():
    """Build the task worker subgraph: recon → rules → context → LLM loop → summarize → extract."""
    tools = get_worker_tools()

    # Inner LLM tool-calling loop
    llm_graph = StateGraph(WorkerState)
    llm_graph.add_node("llm_call", _llm_call)
    llm_graph.add_node("tools", ToolNode(tools))
    llm_graph.set_entry_point("llm_call")
    llm_graph.add_conditional_edges("llm_call", tools_condition)
    llm_graph.add_edge("tools", "llm_call")
    llm_loop = llm_graph.compile()

    # Full worker pipeline
    graph = StateGraph(WorkerState)
    graph.add_node("recon", worker_recon)
    graph.add_node("match_rules", worker_match_rules)
    graph.add_node("deepen_context", worker_deepen_context)
    graph.add_node("llm_loop", llm_loop)
    graph.add_node("summarize", worker_summarize)
    graph.add_node("extract_memory", worker_extract_memory)

    graph.set_entry_point("recon")
    graph.add_edge("recon", "match_rules")
    graph.add_edge("match_rules", "deepen_context")
    graph.add_edge("deepen_context", "llm_loop")
    graph.add_edge("llm_loop", "summarize")
    graph.add_edge("summarize", "extract_memory")
    graph.add_edge("extract_memory", END)

    return graph.compile()
