# Agent Memory Index

CLI args → initial_state dict → graph state (TypedDict, not separate config)
TypedDict Optional[T]: None=use default; Annotated[list, reducer] for message history; Dual-tier MemoryLayer: read_l2/write_l1/write_l2 with L2→L1 summarization flow
Config precedence: CLI args → config file → hardcoded defaults; PlanningConfig with max_iterations/model/auto_approve nested in AgentConfig
Planning loop: user_request gates entry; draft_roadmap + planning_messages track iterations; planning_complete halts; planning_iteration starts at 1 for initial draft
init_agent_structure() provides full dir setup; init_agent_dir(Path) requires explicit path - use former in CLI commands
Recursion limit formula: 100 + (max_iterations × 10) accommodates loop overhead
draft_roadmap pattern: build context dict → call prompt builder → get_llm() for creative work → return draft in state
Test patterns: tmp_agent_dir, _make_state, unittest.mock for LLM [NEW: hybrid git-subprocess mocking + real Git execution; shell cmd error handling: cd-too-many-args fix]
Planning loop (full cycle): draft_roadmap → critique_roadmap → refine_roadmap → write_roadmap; critique uses cheap model; refine sets planning_complete when no major issues or max iterations reached
Draft runs IN STATE, not on disk - roadmap stored in graph state until planning_complete, then written to .agent/roadmap.md
Post-execution: finalize_todo creates TodoSummary in state → extract_session reads summaries from state → distills into lasting memory/rules → post-extraction hook triggers L2→L1 summarization with content-length gating (50 char threshold)
Completed roadmaps are archived to .agent/roadmaps/archive/{date}-{slug}.md
README audit: commits → source files → flag discrepancies by severity (HIGH/MEDIUM/LOW); separate audit from fix phase
architecture/README-structure.md: README reorganization: Architecture → Installation → CLI Reference. Maintenance: audit commits → examine source → identify discrepancies → update.
Undocumented features found: planning mode, tool renames, GCC removal (pl-planning/GCC-refactor commits)
Memory writes (L1/L2): NOT in src/sebba_code/memory/ — distributed across node implementations (context.py, rules.py, deepening.py); memory/ dir is empty/deprecated
Extraction layer (src/sebba_code/memory/extraction.py) writes detailed content to L2 only; condensation pipeline handles L2→L1 async summarization separately
Graph wiring: synchronous downstream for tight coupling (shared state, sequential); async for loose coupling (independent timing)
Cheap model config: _get_cheap_model() + SEBBA_CHEAP_MODEL env var for L2→L1 summarization; default unchanged
Execution nodes: worker.py timeout validated, execute.py/context.py/explore.py gaps pending
Execute subgraph: 6-node workers with timeout/error recovery
architecture/explore-tool-preference-tests.md: Confirm delegate patterns absent from codebase
architecture/plan-architecture.md: Planning loop reviews (draft→critique→refine→write) all in state, no subagent delegation
architecture/exec-flow.md: Execute subgraph (6-node workers) separate from planning phase goals
architecture/planning-nodes.md: added 'Explore Before Planning' directive
architecture/planning-node.md: ## draft_roadmap Node → now enforces explore_before_planning directive
planning-node.md: draft_roadmap→critique_roadmap EXPLRE_PATTERNS → refine_roadmap→write_roadmap
architecture/planning-nodes.md: # Planning Node Architecture / ## Expl Tool Preference: Line 158 specifies direct explore_codebase / raises directive / Tests verify subagent NOT used / TestExploreToolPreference COV=23835 chars / pytest PASS
CLI init subcommand delegates to init_agent_structure() per CLI state flow pattern - uses cwd as default project path
architecture/exec-flow.md: Execute subgraph validated 6-node workers, execute.py/context.py/explore.py gaps pending
architecture/tool-implementation-patterns.md: Execute tools follow code.py pattern, use subprocess for shell compatibility
draft_roadmap→critique EXPLRE_PATTERNS→refine_roadmap→write, no subagent delegation
Hybrid grep+git test verification + environment variable manipulation for config testing
Pre-commit hook 1479 char limit + validate .gitignore/README consistency before commit
Memory extraction writes L2 only; condensation pipeline async gateway→L1 with 50 char threshold
Testrás: importing.py succeeds first, then pytest; LLM mocks need complete response objects
EXPLORE_PATTERNS check catches subagent delegation bypassing human approval gate
EXPLORE_TOOL: Verify planner calls direct tool before delegation
23835 char coverage for explore planning validation
