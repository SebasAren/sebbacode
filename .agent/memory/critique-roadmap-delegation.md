---
topic: critique-roadmap-delegation
source_l2_key: manual
version: 1
created_at: 2026-03-26T00:00:00+00:00
summary_model: manual
---

The `critique_roadmap` node in `src/sebba_code/nodes/planning.py` includes an `EXPLORE_PATTERNS` check that flags when explore tasks are unnecessarily delegated to subagents without human approval. When detected, warnings are returned in `plan_critique` results. Test coverage in `tests/test_nodes/test_planning.py` validates delegation interception using hybrid git-subprocess mocking and real Git execution.

<!-- l2_preview -->
critique_roadmap EXPLORE_PATTERNS check flags unnecessary subagent delegation for explore tasks.
