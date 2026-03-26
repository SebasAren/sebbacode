# Agent Memory Index

CLI args → initial_state dict → graph state (TypedDict, not separate config)
TypedDict Optional[T]: None=use default; Annotated[list, reducer] for message history; Dual-tier MemoryLayer: read_l2/write_l1/write_l2 with L2→L1 summarization flow
Config precedence: CLI args → config file → hardcoded defaults; PlanningConfig with max_iterations/model/auto_approve nested in AgentConfig
Planning loop: user_request gates entry; draft_roadmap + planning_messages track iterations; planning_complete halts; planning_iteration starts at 1 for initial draft
init_agent_structure() provides full dir setup; init_agent_dir(Path) requires explicit path - use former in CLI commands
Recursion limit formula: 100 + (max_iterations × 10) accommodates loop overhead
draft_roadmap pattern: build context dict → call prompt builder → get_llm() for creative work → return draft in state
Test patterns: tmp_agent_dir for file tests; _make_state helper reuse; unittest.mock for LLM; mocks must return complete response objects with required fields, not None
Planning loop (full cycle): draft_roadmap → critique_roadmap → refine_roadmap → write_roadmap; critique uses cheap model; refine sets planning_complete when no major issues or max iterations reached
Draft runs IN STATE, not on disk - roadmap stored in graph state until planning_complete, then written to .agent/roadmap.md
Post-execution: finalize_todo creates TodoSummary in state → extract_session reads summaries from state → distills into lasting memory/rules → post-extraction hook triggers L2→L1 summarization with content-length gating (50 char threshold)
Completed roadmaps are archived to .agent/roadmaps/archive/{date}-{slug}.md
README audit: commits → source files → flag discrepancies by severity (HIGH/MEDIUM/LOW); separate audit from fix phase
## README Maintenance Pattern / Audit: git commits → source files → structural gaps, not formatting
architecture/README-structure.md: README reorganization: Architecture → Installation → CLI Reference. Maintenance: audit commits → examine source → identify discrepancies → update.
Audit vs update phases must be tracked separately; audit discovers, update applies fixes. README: audit commits → examine source → identify discrepancies → update → verify with markdown checks (README audit task)
Undocumented features found: planning mode, tool renames, GCC removal (pl-planning/GCC-refactor commits)
audit/undocumented-features-verification.md: # Audit Report: Undocumented Features Verification / **Date**: 2026-03-26 / **Auditor**: Source Code Audit / Undocumented: planning mode, tool renames, GCC removal (pl-planning/GCC-refactor commits)
Memory writes (L1/L2): NOT in src/sebba_code/memory/ — distributed across node implementations (context.py, rules.py, deepening.py); memory/ dir is empty/deprecated
Extraction layer (src/sebba_code/memory/extraction.py) writes detailed content to L2 only; condensation pipeline handles L2→L1 async summarization separately
Graph wiring: synchronous downstream for tight coupling (shared state, sequential); async for loose coupling (independent timing)
Cheap model config: _get_cheap_model() + SEBBA_CHEAP_MODEL env var for L2→L1 summarization; default unchanged
Test patterns: tmp_agent_dir for file tests; _make_state helper reuse; unittest.mock for LLM; env vars via monkeypatch
