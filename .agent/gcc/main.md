# Goal

Add a planning loop to the agent graph that transforms a user's natural language request into a well-structured, validated roadmap before execution begins. This replaces the one-shot `seed` approach with an iterative draft-critique-refine cycle integrated into the LangGraph flow.

## Context

Currently `sebba-code seed "title"` does a single LLM call to generate a roadmap, with no validation against the actual codebase. The `explore_validate` node catches some issues post-hoc, but by then the roadmap is already committed to disk. A planning loop would produce higher-quality roadmaps by iterating before persisting.

## Todos

- [x] Define planning loop state fields in `src/sebba_code/state.py` (`user_request`, `draft_roadmap`, `planning_messages`, `planning_iteration`, `planning_complete`) and add `needs_planning` routing conditional
- [x] ~~Add `sebba-code plan "description"` CLI command in `src/sebba_code/cli.py` that passes the user request into graph state~~ → Implemented with full initial state, streaming event handling, and NotImplementedError handling. Planning loop nodes still need implementation.
- [x] Create planning prompt templates (draft, critique, refine) in `src/sebba_code/prompts.py` or a new `planning_prompts.py`
- [x] ~~Implement `draft_roadmap` node in `src/sebba_code/nodes/planning.py` — takes user request + loaded context (L0 memory, git state, codebase structure) and generates initial roadmap draft in state (not on disk)~~
- [x] ~~Implement `critique_roadmap` node in `src/sebba_code/nodes/planning.py` — validates draft against codebase (file existence, todo ordering, vague descriptions, scope creep), outputs structured fixes using cheap model~~
- [x] ~~Implement `refine_roadmap` node in `src/sebba_code/nodes/planning.py` — applies critique fixes to draft, increments `planning_iteration`, sets `planning_complete` when critique has no major issues or max iterations reached~~
- [x] ~~Implement `write_roadmap` node that persists the finalized draft to `.agent/gcc/main.md`~~
- [x] ~~Wire the planning loop into `src/sebba_code/graph.py`: `load_context → [needs_planning?] → draft_roadmap → critique_roadmap → [planning_complete?] yes → write_roadmap → read_roadmap, no → refine_roadmap → critique_roadmap`~~
- [x] ~~Add config options to `src/sebba_code/config.py`: `planning.max_iterations` (default 3), `planning.model`, `planning.auto_approve` (default false)~~ → Implemented PlanningConfig dataclass with three fields (max_iterations, model, auto_approve), integrated into AgentConfig, updated default config YAML in seed.py, updated planning.py to use config via _get_max_iterations() and _get_planning_model(), updated cli.py plan() command to read from config when CLI arg not provided. All 33 tests pass.
- [x] ~~Write tests in `tests/test_nodes/test_planning.py` covering draft output format, critique detection, refine application, loop termination, and file persistence~~

## Target Files

- src/sebba_code/state.py
- src/sebba_code/graph.py
- src/sebba_code/cli.py
- src/sebba_code/config.py
- src/sebba_code/prompts.py
- src/sebba_code/nodes/planning.py
- src/sebba_code/seed.py
- tests/test_nodes/test_planning.py

## Active Branches

## Decisions Made

## Constraints

- The planning loop must produce markdown in the exact format `read_roadmap` expects (same sections, same todo regex)
- Draft must stay in state until finalized — no writing to disk during iteration
- Critique node should use the cheap model to keep costs low
- Backward compatibility: `sebba-code seed` without `--refine` must keep current one-shot behavior
- Max 3 planning iterations by default to bound LLM costs
