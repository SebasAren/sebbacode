---
topic: tool-patterns
source_l2_key: consolidated
version: 2
created_at: 2026-03-28
summary_model: manual
---

# Tool Implementation Patterns

## Code.py Pattern (Shell Commands)

All execution tools that run shell commands MUST follow the `code.py` pattern using `subprocess`:

```python
import subprocess

def run_command(command: str) -> str:
    result = subprocess.run(
        command, shell=True, capture_output=True, text=True, timeout=30
    )
    if result.returncode != 0:
        return f"Error: {result.stderr}"
    return result.stdout
```

- Use `subprocess.run()` for shell compatibility
- Capture both stdout and stderr
- Set reasonable timeouts
- Return error output on non-zero exit codes

## Tool Registration

New tools MUST be registered in both:
- `get_all_tools()` — full toolset for orchestrator
- `get_worker_tools()` — restricted toolset for task workers

Worker-restricted tools (NOT available to workers):
- `explore` — create git worktrees
- `try_approach` — record implementation attempts
- `evaluate` — pick winning approach
- `adopt` — merge winner and cleanup

Worker-available tools:
- `read_file`, `write_file`, `run_command`
- `search_code`, `search_files`
- `explore_codebase` (LLM-guided exploration)
- `mark_todo_done`, `signal_blocked`, `add_subtask`
- `memory_query`

## Full Tool Registry (8 tools)

| Tool | Module | Type |
|------|--------|------|
| `read_file` | `code.py` | I/O |
| `write_file` | `code.py` | I/O |
| `run_command` | `code.py` | Execution |
| `search_code` | `search.py` | Search |
| `search_files` | `search.py` | Search |
| `explore_codebase` | `explore_agent.py` | Exploration |
| `mark_todo_done` | `progress.py` | Progress |
| `add_subtask` | `progress.py` | Progress |
| `signal_blocked` | `progress.py` | Progress |
| `explore` | `exploration.py` | Exploration |
| `try_approach` | `exploration.py` | Exploration |
| `evaluate` | `exploration.py` | Exploration |
| `adopt` | `exploration.py` | Exploration |
| `memory_query` | `memory.py` | Memory |

## Execution Limits

- `max_tool_calls_per_task`: 50 (configurable in config.yaml)
- `llm_timeout`: 120 seconds per LLM call
- `max_parallel_workers`: 3 (configurable)
- Recursion limit: `100 + (max_iterations × 10)` — accommodates planning loop overhead

## Pre-commit Hook

- Maximum 1479 characters for `.git/hooks/pre-commit`
- Must validate: `.gitignore` entries exist, README sections consistent, codebase structure
- Hook created/managed by agent, not manually

<!-- l2_preview -->
Consolidated from tool-implementation-patterns.md, patterns.md, loaded.md and their L2 directories.
