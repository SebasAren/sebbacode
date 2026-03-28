# PROJECT KNOWLEDGE BASE

**Generated:** 2026-03-28
**Commit:** 670a900
**Branch:** main

## OVERVIEW
LangGraph coding agent with git-native tiered memory (L0/L1/L2). Plans tasks via iterative draft-critique loop, executes via parallel DAG dispatch.

## STRUCTURE
```
sebba-code/
├── src/sebba_code/     # Main package (src-layout)
│   ├── nodes/           # 13 graph nodes (planning, dispatch, worker, etc.)
│   ├── tools/          # 8 LLM-callable tools (code, search, memory, etc.)
│   ├── helpers/        # Utilities (git, markdown, parsing, rules)
│   └── memory/         # Tiered memory system (L1/L2 with LLM summarization)
├── tests/              # Mirrors src structure
├── .agent/             # Agent runtime state (memory, rules, sessions)
├── mise.toml           # Task runner (uv-based)
└── pyproject.toml      # Package config (hatchling)
```

## WHERE TO LOOK
| Task | Location | Notes |
|------|----------|-------|
| Graph definition | `src/sebba_code/graph.py` | 12-node StateGraph |
| CLI commands | `src/sebba_code/cli.py` | run/init/plan/seed/status |
| Node implementations | `src/sebba_code/nodes/` | One file per node |
| Agent tools | `src/sebba_code/tools/` | Worker toolset |
| Memory system | `src/sebba_code/memory/` | L0/L1/L2 layers |
| Config | `src/sebba_code/config.py` | SEBBA_* env var handling |

## CODE MAP

| Symbol | Type | Location | Role |
|--------|------|----------|------|
| `build_agent_graph` | fn | `graph.py:22` | Compiles unified StateGraph |
| `AgentState` | TypedDict | `state.py:88` | Unified graph state schema |
| `Task` | TypedDict | `state.py:41` | DAG task node |
| `TaskResult` | TypedDict | `state.py:55` | Worker output schema |
| `get_ready_tasks` | fn | `dispatch.py:14` | DAG scheduling logic |
| `build_task_worker` | fn | `worker.py` | Creates worker subgraph |
| `get_all_tools` | fn | `tools/__init__.py:19` | Full tool registry |
| `get_worker_tools` | fn | `tools/__init__.py:40` | Worker-restricted tools |

## CONVENTIONS (THIS PROJECT)

- **Python 3.11+**, src-layout (`src/sebba_code/`)
- **Build:** hatchling via `pyproject.toml`, not setuptools
- **Task runner:** mise.toml (not Makefile)
- **LangGraph version:** >=0.4 (uses `Send` fan-out, `Command` routing)
- **State:** Single TypedDict (`AgentState`) passed through all nodes
- **Worker communication:** `Send()` for fan-out, `Command(goto=...)` for routing
- **Planning loop:** draft → critique → refine (max 3 iterations)
- **LLM calls:** `invoke_with_timeout` (main), `invoke_structured` (Pydantic output)
- **Memory:** Async LLM summarization via `post_extraction_hook`

## ANTI-PATTERNS (THIS PROJECT)

- **NEVER** include real API keys in code/docs (use `your-api-key-here` placeholders)
- Do not mark integration tests with `@pytest.mark.integration` on unit test runs
- Do not commit to `.agent/` directories (git-ignored, agent state only)

## UNIQUE STYLES

- **Graph nodes as files:** Each node is a separate Python file in `nodes/`
- **Tiered memory:** L0 index (~500 tokens, always loaded) → L1 summaries (~2000 tokens) → L2 detailed entries (~4000 tokens)
- **Path-scoped rules:** `.agent/rules/*.md` with YAML frontmatter `paths:` globs
- **Exploration via worktrees:** Uses git worktrees under `.agent/worktrees/` for parallel approach exploration

## COMMANDS
```bash
uv pip install -e .                    # Install (editable)
uv run sebba-code run "task" --verbose # Run agent
uv run pytest tests/ -v                # Unit tests only
uv run pytest -m integration -v        # Integration tests (real LLM)
ruff check src/sebba_code/             # Lint
```

## NOTES

- Integration tests require real LLM endpoint (`-m integration` flag)
- Default pytest excludes integration (`-m 'not integration'`)
- `sebba_code.constants.init_agent_dir()` overrides global agent dir (used in tests)
- Workers use restricted toolset (no `explore`/`try_approach`/`evaluate`/`adopt`)
- `CLAUDE.md` exists at root for AI assistant guidance
