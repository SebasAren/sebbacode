---
topic: planning
source_l2_key: consolidated
version: 2
created_at: 2026-03-28
summary_model: manual
---

# Planning System

## Planning Loop

The planning phase uses an iterative draft-critique-refine cycle:

```
plan_draft → plan_critique → plan_refine → [complete?] → build_dag
```

1. **plan_draft**: Creates initial roadmap from user request + memory context. Uses creative model (`get_llm()`). Roadmap stored in graph state, NOT on disk.
2. **plan_critique**: Evaluates with cheap model. Checks for issues including `EXPLORE_PATTERNS` violations.
3. **plan_refine**: Addresses critique feedback. Sets `planning_complete=True` when no major issues remain or `max_iterations` reached (default: 3).
4. **build_dag**: Converts roadmap todos into executable task DAG with dependency edges.

## Explore Before Planning

**Critical rule**: `draft_roadmap` MUST call `explore_codebase` tool directly on state BEFORE creating any subagent tasks.

Enforcement layers:
1. **Prompt directive** in `planning_prompts.py` (Line 158): Explicit instruction to call explore first
2. **Runtime validation** in `critique_roadmap`: `EXPLORE_PATTERNS` regex scans roadmaps for tasks delegated to subagents without explicit human approval

This prevents autonomous planning without initial context audit.

## Roadmap Lifecycle

- During planning: roadmap lives in graph state (`draft_roadmap` field)
- After `planning_complete=True`: written to `.agent/roadmap.md`
- After execution: archived to `.agent/roadmaps/archive/{date}-{slug}.md`
- Format: Goal → Context → Todos (with checkboxes) → Target Files → Active Branches → Decisions Made → Constraints

## DAG Dispatch

- `get_ready_tasks()` finds tasks with all dependencies satisfied
- `dispatch_tasks` fans out via `Send("task_worker", per_task_state)`
- `collect_results` gathers `TaskResult` from each worker
- Loop continues until `is_dag_complete()` or `is_dag_deadlocked()`
- `human_approval` node gates execution (skip with `--auto-approve`)

## Recursion Limit

Formula: `100 + (max_iterations × 10)` — base 100 for setup nodes, 10 per planning iteration for loop overhead.

<!-- l2_preview -->
Consolidated from planning-node.md, planning-nodes.md, explore-task-delegation.md, critique-roadmap-delegation.md and their L2 directories.
