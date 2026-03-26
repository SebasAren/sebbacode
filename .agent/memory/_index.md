# Agent Memory Index

CLI args → initial_state dict → graph state (TypedDict, not separate config)
TypedDict Optional[T]: None=use default; TYPE_CHECKING for AgentState avoids circular imports; Annotated[list, reducer] for message history
Conditional state population: only set Optional fields when explicitly provided
Config precedence: CLI args → config file → hardcoded defaults; PlanningConfig with max_iterations/model/auto_approve nested in AgentConfig
Conditional edge routing: return 'yes'/'no' strings; absence of trigger field = backward-compatible pass-through
Planning loop: user_request gates entry; draft_roadmap + planning_messages track iterations; planning_complete halts; planning_iteration starts at 1 for initial draft
Graceful degradation: try/except NotImplementedError; truncation helpers prevent token overflow from L0/L1/L2 memory
init_agent_structure() provides full dir setup; init_agent_dir(Path) requires explicit path - use former in CLI commands
Recursion limit formula: 100 + (max_iterations × 10) accommodates loop overhead
Constants in cli.py (e.g., DEFAULT_PLANNING_MAX_ITERATIONS): use temporary default until config module implements the setting
draft_roadmap pattern: build context dict → call prompt builder → get_llm() for creative work → return draft in state
Test patterns: tmp_agent_dir for file tests; _make_state helper reuse; unittest.mock for LLM; high max_iterations in iteration tests; shutil.rmtree for non-empty dirs
LLM nodes in planning.py reuse existing client pattern from codebase (not new implementation)
Test verification: import test first, then pytest - path matters for module resolution; YAML config loading verified; backward compatibility with existing configs
Title authoritative over description when they conflict; backward-compatible config: empty string or None in Optional fields triggers default behavior
Planning loop (full cycle): draft_roadmap → critique_roadmap → refine_roadmap; critique uses cheap model for validation; refine sets planning_complete when no major issues or max iterations reached
GCC commit files: finalize_todo in extract.py produces .agent/gcc/*.md files (not a dedicated extraction step) | PlanningConfig dataclass: max_iterations=3 (safety), model='' (system LLM), auto_approve=false (conservative security); constructor overrides YAML config
Draft runs IN STATE, not on disk - roadmap stored in graph state until planning_complete
Planning prompts template: src/sebba_code/nodes/planning_prompts.md - separate template file for draft stage prompts
Planning loop: draft_roadmap (generates draft from user_request + L0/git/codebase context) → critique_roadmap (cheap model validates existence/ordering/vagueness/scope) → refine_roadmap (applies fixes, increments iteration, sets planning_complete) → write_roadmap (persists to .agent/gcc/main.md)
Planning loop: load_context → [needs_planning?] → draft_roadmap → critique_roadmap → [planning_complete?] yes → write_roadmap → read_roadmap, no → refine_roadmap → critique_roadmap; user_request gates entry; draft_roadmap+planning_messages track iterations; planning_complete halts; planning_iteration counts cycles
Config loading: YAML with dataclass defaults; CLI args override config values; Conditional state population only for explicitly provided Optional fields
architecture/planning-system.md: draft_roadmap extracts user_request + memory L0/L1/L2 + roadmap/briefing/target_files from state, uses planning prompt with LLM to generate initial roadmap draft stored in state (not on disk) / GCC commit files (`.agent/gcc/*.md`) use timestamp-based format produced by `finalize_todo` in `src/sebba_code/nodes/extract.py` / `commit_changes` node must read same file patterns to integrate with existing workflow
