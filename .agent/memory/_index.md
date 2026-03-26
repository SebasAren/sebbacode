# Agent Memory Index

CLI args → initial_state dict → graph state (TypedDict, not separate config)
TypedDict Optional[T]: None=use default; Annotated[list, reducer] for message history
Config precedence: CLI args → config file → hardcoded defaults; PlanningConfig with max_iterations/model/auto_approve nested in AgentConfig
Planning loop: user_request gates entry; draft_roadmap + planning_messages track iterations; planning_complete halts; planning_iteration starts at 1 for initial draft
init_agent_structure() provides full dir setup; init_agent_dir(Path) requires explicit path - use former in CLI commands
Recursion limit formula: 100 + (max_iterations × 10) accommodates loop overhead
draft_roadmap pattern: build context dict → call prompt builder → get_llm() for creative work → return draft in state
Test patterns: tmp_agent_dir for file tests; _make_state helper reuse; unittest.mock for LLM
Planning loop (full cycle): draft_roadmap → critique_roadmap → refine_roadmap → write_roadmap; critique uses cheap model; refine sets planning_complete when no major issues or max iterations reached
Draft runs IN STATE, not on disk - roadmap stored in graph state until planning_complete, then written to .agent/roadmap.md
Post-execution: finalize_todo creates TodoSummary in state → extract_session reads summaries from state → distills into lasting memory/rules
Completed roadmaps are archived to .agent/roadmaps/archive/{date}-{slug}.md
README audit: git log → source files comparison → flag undocumented features (worktree, LangGraph, Python-only, tools)
## README Maintenance Pattern / Audit: git commits → source files → structural gaps, not formatting
architecture/README-structure.md: README reorganization: Architecture → Installation → CLI Reference. Maintenance: audit commits → examine source → identify discrepancies → update.
Audit vs update phases must be tracked separately - don't mark fixes done when only audit is complete
Undocumented features found: planning mode, tool renames, GCC removal (pl-planning/GCC-refactor commits)
