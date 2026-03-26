---
topic: planning-nodes
source_l2_key: manual
version: 1
created_at: 2026-03-26T00:00:00+00:00
summary_model: manual
---

A directive in `draft_plan_prompt` (`src/sebba_code/planning_prompts.py`, 6 lines) enforces that the planner must call the explore tool directly BEFORE creating subagent tasks. The planning node at `src/sebba_code/nodes/planning.py:158` specifies `direct explore_codebase` execution. `TestExploreToolPreference` in `tests/test_nodes/test_planning.py` validates direct tool exploration takes precedence over spawning subagent processes.

<!-- l2_preview -->
Explore-before-planning directive enforces direct explore tool usage before subagent task creation.
