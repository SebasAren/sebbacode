## Goal
Add a git commit step to the workflow that automatically commits changes after memory extraction, using commit files produced during the extraction/generation process. This automates the version control workflow and ensures extracted memory and generated code changes are tracked.

## Context
The codebase has a planning loop (draft_roadmap → critique_roadmap → refine_roadmap) and memory extraction with L0/L1/L2 truncation helpers. Currently, changes generated during the workflow are not automatically committed. The "gcc commit files" likely refer to generated commit message files or change manifests produced by memory extraction or the planning nodes. This feature closes the loop by committing those outputs to git.

## Todos
- [x] ~~Examine memory extraction nodes to identify where "gcc commit files" are produced and what format they use~~ → Found gcc commit files are produced by finalize_todo node in src/sebba_code/nodes/extract.py. Format: Markdown files at <agent_dir>/gcc/commits/<num>.md with # Commit header, What I Did, Decisions Made, Files Touched sections.
- [x] ~~Create `commit_changes` node function in `src/sebba_code/nodes/planning.py` that reads commit files and executes git add + git commit~~
- [x] ~~Update graph routing in `src/sebba_code/graph.py` to add edge from memory extraction → commit_changes~~
- [ ] Add `commit_on_complete` config option to `PlanningConfig` in `src/sebba_code/config.py` (default: False for backward compatibility)
- [ ] Implement conditional commit logic: only commit if `commit_on_complete=True` or explicit trigger field present
- [ ] Add unit tests in `tests/test_nodes/test_planning.py` for commit node with mocked git subprocess calls
- [ ] Test full cycle: ensure commit happens only after successful memory extraction completes

- [ ] Add todo: Create the `src/sebba_code/` package structure (init files, directory hierarchy) before implementing the planned nodes and config.
## Target Files
- src/sebba_code/__init__.py (NEW - create first)
- src/sebba_code/nodes/__init__.py (NEW)
- src/sebba_code/nodes/planning.py (NEW - add commit_changes)
- src/sebba_code/graph.py (NEW)
- src/sebba_code/config.py (NEW - create PlanningConfig with commit_on_complete)
- tests/__init__.py (NEW)
- tests/test_nodes/__init__.py (NEW)
- tests/test_nodes/test_planning.py (NEW)
## Active Branches
- `feature/git-commit-after-memory-extraction` (create)

## Decisions Made
- Commit step is conditional (opt-in via config) to preserve existing behavior
- Uses subprocess for git commands to match existing patterns in codebase
- Returns commit hash in state for traceability
- Failure to commit does not halt workflow (graceful degradation with warning)

## Constraints
- Must not break existing planning loop iteration behavior
- Backward compatible: existing configs without `commit_on_complete` default to current behavior
- Git operations should be idempotent where possible
- Follow existing node pattern: return state dict, use typed hints, handle NotImplementedError
- Add constraint: The 'Context' section references 'memory extraction with L0/L1/L2 truncation helpers' and a 'planning loop' but no such code exists in the codebase.