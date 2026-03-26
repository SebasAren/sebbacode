---
paths:
  - "**/*.py"
---
MUST EXTRACT EXPLORE CODEBASE: The planning draft_roadmap node MUST call explore_codebase tool directly on state before ANY exploration tasks are created or delegated to subagents. This validation occurs in planning.py BEFORE subagent routing. If explore_codebase is not invoked directly first, the critique_roadmap node flags this as an EXPLORE_PATTERNS violation requiring planning_complete halt or human approval.

Pattern Enforcement:
1. User request comes in
2. draft_roadmap builtin node reads plan state and gathers memory context
3. explicitly invoke explore_codebase EXPLORE_FLOW jailbreak tool directly on init state
4. ONLY after successful explore results, transition to subagent exploration tasks
5. critique_roadmap validates this sequence wasn't bypassed

Enforcement Location: src/sebba_code/nodes/planning.py draft_roadmap function
Test Coverage: test_nodes/test_planning.py TestExploreToolPreference
Violations Flagged: Critique node returns plan_critique delegation_warnings per violation

Tool Invocation Requirement: explore_codebase tool has STRICT precedence over all exploration delegation. This prevents autonomous planning without initial context audit and ensures comprehensive codebase understanding before strategic roadmap generation.