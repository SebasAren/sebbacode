
## Path Issues

When running pytest from wrong directory, import paths fail. Always run from correct repo root.
**Test sequence**: (1) verify import succeeds, (2) run pytest
### Planning Node Test Patterns
- `tmp_agent_dir` fixture: Use for file persistence tests requiring `.agent/` directory structure
- `_make_state` helper: Reuse existing pattern from `tests/test_nodes/` for consistent state creation
- Mock LLM with `unittest.mock`: Simulate agent behavior without external API calls
- Iteration count in tests: Set `max_iterations` high enough (e.g., 10) to avoid early loop completion when testing specific iteration behavior
- Directory cleanup: Use `shutil.rmtree()` for non-empty directories, not `tmp_path` removal