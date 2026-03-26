---
topic: loaded
source_l2_key: manual
version: 1
created_at: 2026-03-26T00:00:00+00:00
summary_model: manual
---

Completed graph nodes: `summarize_to_l1`, `dispatch_tasks`, `human_approval`, `collect_results`. All follow `node_function(state) -> state` pattern, executing sequentially in `graph.py` with shared TypedDict state. Pre-commit hook validates node implementations conform to state requirements.

<!-- l2_preview -->
Graph nodes: summarize_to_l1, dispatch_tasks, human_approval, collect_results. Pattern: node_function(state) -> state.
