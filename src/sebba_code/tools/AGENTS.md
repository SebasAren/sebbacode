# Agent Tools

**Parent:** `AGENTS.md` (root)
**Score:** 10 — distinct domain

## OVERVIEW
8 Python modules exposing LLM-callable tools. Tools are functions decorated with `@tool` (from langchain-core).

## STRUCTURE
```
tools/
├── __init__.py        # get_all_tools() + get_worker_tools()
├── code.py            # read_file, write_file, run_command
├── search.py          # search_code, search_files
├── memory.py          # memory_query
├── progress.py        # mark_task_done, signal_blocked, add_subtask
├── explore_agent.py  # explore_codebase (LLM-guided exploration)
├── exploration.py     # explore, try_approach, evaluate, adopt (git worktrees)
└── git_commit.py      # git_commit (conventional commits)
```

## TOOL REGISTRY

| Tool | Function | Purpose |
|------|----------|---------|
| `read_file` | `code.py` | Read file with truncation (>5000 chars → summarize) |
| `write_file` | `code.py` | Write content, creates parent dirs |
| `run_command` | `code.py` | Shell exec with output capture |
| `search_code` | `search.py` | grep-like content search |
| `search_files` | `search.py` | glob pattern file search |
| `explore_codebase` | `explore_agent.py` | LLM-guided multi-step exploration |
| `mark_task_done` | `progress.py` | Update task status in graph state |
| `signal_blocked` | `progress.py` | Mark task blocked + reason |
| `add_subtask` | `progress.py` | Add new task to DAG |
| `memory_query` | `memory.py` | Search agent memory (L0/L1/L2) |
| `explore` | `exploration.py` | Create git worktree for exploration |
| `try_approach` | `exploration.py` | Record attempt in worktree |
| `evaluate` | `exploration.py` | Pick winner from attempts |
| `adopt` | `exploration.py` | Merge winner, cleanup worktrees |
| `git_commit` | `git_commit.py` | Conventional commit creation |

## WORKER TOOLSET

`get_worker_tools()` returns 10 tools (excludes exploration tools):
- read_file, write_file, run_command, search_files, search_code, explore_codebase
- mark_task_done, signal_blocked, add_subtask, memory_query

`get_all_tools()` returns 14 tools (includes exploration + git_commit).

## CONVENTIONS

- Tools use `@tool` decorator from `langchain_core.tools`
- Docstrings become tool descriptions in LLM context
- `run_command` captures stdout/stderr, returns combined output
- `read_file` truncates at 5000 chars with summarization fallback
- Exploration tools use git worktrees under `.agent/worktrees/`

## NOTES

- No file delete tool — deletion via `write_file` with empty content
- `git_commit.py` uses `ConventionalCommit` dataclass with type/scope/description
- `exploration.py` tools are worker-restricted (not in worker toolset)
- Memory query uses semantic search across L0/L1/L2 index
