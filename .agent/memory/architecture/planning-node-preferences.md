EXPLORE_TOOL_PREFERENCE PATTERN (Test Explore Tool Preference) 

**NEW KNOWLEDGE**: Test coverage added to verify planner (draft_roadmap) strictly prefers direct explore_codebase tool CALLS before routing exploration to subagents.

**Location**: `src/sebba_code/nodes/planning.py` / `tests/test_nodes/test_planning.py`

**Coverage**: TestExploreToolCoverage added, 23835 chars / TestExploreToolPreference validation confirmed

**Enforcement**: Line 158 of `src/sebba_code/planning_prompts.py` specifies direct explore_codebase invocation must precede subagent routing

**Test Approach**: Hybrid mocking - git subprocess simulation combined with real Git execution for integration verification

**Purpose**: Prevents planner from delegating exploration tasks to subagents without first executing explore_codebase tool directly on current state. Ensures context is fully audited before any autonomous delegation occurs.

**Pattern**: Draft_roadmap node validates tool usage sequence → Critique_roadmap validates EXPLORE_PATTERNS compliance → Refine_roadmap finalizes only if no violations

**Test Pattern**: assert that explore tasks require auto_approve flag if delegated to subagents without prior direct tool invocation

**Architectural Impact**: Distinguishes between "direct exploration" (safe, documented) and "subagent exploration" (requires human oversight). Prevents autonomous planning drift.