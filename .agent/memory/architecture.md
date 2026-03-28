---
topic: architecture
source_l2_key: consolidated
version: 2
created_at: 2026-03-28
summary_model: manual
---

# Architecture

## Graph Structure

The agent runs as a LangGraph `StateGraph` with 12+ nodes organized in 4 phases:

1. **Load & Bootstrap** — `load_context` → `needs_bootstrap` → `explore_bootstrap` (or skip to plan_recon)
2. **Plan** — `plan_recon` → `plan_draft` → `plan_critique` → `plan_refine` → `build_dag` → `human_approval`
3. **Execute** — `dispatch_tasks` → `task_worker` (fan-out via `Send`) → `collect_results` → loop until DAG complete
4. **Extract** — `extract_session` → `summarize_to_l1` → END

## Worker Subgraph

Each task runs through a 6-node worker subgraph (built in `worker.py`, 729 lines):

```
worker_recon → worker_match_rules → worker_deepen_context → llm_call → worker_summarize → extract_to_parent
```

- `worker_recon`: Builds briefing from target files, imports, tests, git history
- `worker_match_rules`: Loads path-scoped rules for target files
- `worker_deepen_context`: LLM selects relevant L1/L2 memory
- `llm_call`: Invoke LLM with tools, loop until done or max_calls reached
- `worker_summarize`: Extract TaskResult from worker run
- `extract_to_parent`: Format output for parent graph

## State Management

- Single `AgentState` TypedDict passed through all nodes
- `Optional[T]` fields: `None` = use default value
- `Annotated[list, reducer]` for message history accumulation
- CLI args → `initial_state` dict → graph state (no separate config object)
- Config precedence: CLI args → config.yaml → hardcoded defaults
- `PlanningConfig` nested in `AgentConfig` with `max_iterations`/`model`/`auto_approve`

## Key Source Files

| Component | File | Key Function |
|-----------|------|--------------|
| Graph assembly | `graph.py` | `build_agent_graph()` |
| State schema | `state.py` | `AgentState`, `Task`, `TaskResult` |
| DAG scheduling | `dispatch.py` | `get_ready_tasks()`, `is_dag_complete()` |
| Worker subgraph | `worker.py` | `build_task_worker()` |
| CLI commands | `cli.py` | run/init/plan/seed/status |
| Config | `config.py` | SEBBA_* env var handling |

## Conventions

- Node functions: `def node_name(state: AgentState) -> dict`
- Conditional routing: `Literal["yes", "no"]` or `Command(goto=...)`
- Fan-out: `Send("task_worker", per_task_state)` for parallel dispatch
- Workers receive `WorkerState` (per-task), return `WorkerOutput`
- `init_agent_structure()` creates `.agent/` dirs; `init_agent_dir(Path)` overrides global
- `uv pip install -e .` for editable install, `uv pip install -e ".[dev]"` for dev deps

<!-- l2_preview -->
Consolidated from 15+ L1/L2 files covering architecture, loaded nodes, graph-nodes, cli-state-flow, execute-subgraph.