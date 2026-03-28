# Graph Nodes

**Parent:** `AGENTS.md` (root)
**Score:** 18 — high complexity, distinct domain

## OVERVIEW
13 Python files, each implementing a node in the LangGraph StateGraph. Nodes are pure functions: `state → state` or `state → Command`.

## STRUCTURE
```
nodes/
├── graph.py          # build_agent_graph() — assembles all nodes
├── __init__.py      # Empty (namespace only)
├── approval.py       # human_approval node + build_dag
├── context.py       # worker_deepen_context — LLM selects memory
├── dispatch.py      # dispatch_tasks + collect_results
├── execute.py       # DAG execution helpers
├── explore.py       # explore_bootstrap + worker_recon
├── extract.py       # extract_session — L2 extraction
├── load_context.py  # load_context + needs_bootstrap
├── plan_recon.py    # plan_recon — codebase recon
├── planning.py      # plan_draft + plan_critique + plan_refine
├── rules.py         # worker_match_rules
├── summarize.py     # summarize_to_l1
└── worker.py        # build_task_worker + task_worker subgraph (729 lines)
```

## WHERE TO LOOK
| Node | File | Key Function |
|------|------|--------------|
| Planning loop | `planning.py` | `plan_draft`, `plan_critique`, `is_planning_complete` |
| Task DAG | `dispatch.py` | `get_ready_tasks`, `is_dag_complete`, `is_dag_deadlocked` |
| Worker subgraph | `worker.py` | `build_task_worker()` returns compiled subgraph |
| Memory extraction | `extract.py` | `extract_session` writes L2 entries |
| Bootstrap | `explore.py` | `explore_bootstrap` for new codebases |

## CONVENTIONS

- Node functions named by verb: `load_context`, `plan_draft`, `dispatch_tasks`
- Conditional routing returns `Literal["yes", "no"]` or `Literal["path1", "path2"]`
- Bootstrap uses `needs_bootstrap` conditional: `"yes"` → `explore_bootstrap`, `"no"` → `plan_recon`
- Workers receive `WorkerState` (per-task), return `WorkerOutput`
- `Command(goto=...)` for programmatic routing without edges

## KEY PATTERNS

```python
# Node signature pattern
def node_name(state: AgentState) -> AgentState:
    ...

# Conditional edge pattern
graph.add_conditional_edges("node", condition_fn, {"yes": "next", "no": "other"})

# Fan-out via Send (dispatch.py pattern)
return Command(goto=Send("task_worker", {"task": task, ...}))

# Worker subgraph flow
worker: worker_recon → worker_match_rules → worker_deepen_context → llm_call → END
```

## WORKER SUBGRAPH DETAIL

`worker.py` contains 729-line task worker subgraph with 6 nodes:
1. `worker_recon` — builds briefing from target files
2. `worker_match_rules` — loads path-scoped rules
3. `worker_deepen_context` — LLM selects relevant L1/L2 memory
4. `llm_call` — invoke LLM with tools, loop until done or max_calls
5. `worker_summarize` — extract TaskResult from worker run
6. `extract_to_parent` — format output for parent graph

## NOTES

- `worker.py` is the largest file — complex tool-calling loop
- `planning.py` uses `EXPLORE_PATTERNS` regex to identify investigation tasks
- `dispatch.py` has task factory `_task()` helper in tests
- `summarize.py` uses cheap LLM for L2→L1 condensation
