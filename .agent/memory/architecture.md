---
topic: architecture
source_l2_key: manual
version: 1
created_at: 2026-03-26T00:00:00+00:00
summary_model: manual
---

CLI arguments flow through `initial_state` dict into LangGraph `AgentState` TypedDict (not separate config objects), using `Optional[T]` where `None` means "apply default". The execute subgraph in `src/sebba_code/nodes/execute.py` uses a 6-node worker pattern with timeout/error recovery. New graph nodes are wired as synchronous downstream edges in `graph.py` and return dicts merged into state. LLM config uses `_get_cheap_model()` / `_get_model()` helpers with `SEBBA_*` env var fallbacks; cheap model is used for critique/summarization. Memory writes are distributed across node implementations in `src/sebba_code/nodes/` (context.py, rules.py, deepening.py), not centralized. The `MemoryLayer` provides dual-tier L2/L1 storage with content-length gated summarization. The `draft_roadmap` node builds context from user_request, memory, git_state, and codebase_structure, invokes the main LLM, and returns `{"draft_roadmap": content, "planning_iteration": 1}`. Installation uses `uv pip install -e .` with `uv.lock` in repo.

<!-- l2_preview -->
CLI args -> initial_state dict -> graph state (TypedDict, not separate config). Execute subgraph: 6-node workers with timeout/error recovery.
