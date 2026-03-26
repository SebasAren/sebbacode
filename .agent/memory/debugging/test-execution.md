
## Path Issues

When running pytest from wrong directory, import paths fail. Always run from correct repo root.
**Test sequence**: (1) verify import succeeds, (2) run pytest
### Planning Node Test Patterns
- `tmp_agent_dir` fixture: Use for file persistence tests requiring `.agent/` directory structure
- `_make_state` helper: Reuse existing pattern from `tests/test_nodes/` for consistent state creation
- Mock LLM with `unittest.mock`: Simulate agent behavior without external API calls
- Iteration count in tests: Set `max_iterations` high enough (e.g., 10) to avoid early loop completion when testing specific iteration behavior
- Directory cleanup: Use `shutil.rmtree()` for non-empty directories, not `tmp_path` removal
## Mocking Async Functions with Response Objects
When mocking async functions like `invoke_with_timeout`, the mock cannot return `None`. It must return a properly structured response object with all required fields. For example, when testing L1Summary objects, the mock chain must return objects with `file`, `topic`, and `summary` fields.

**Symptom**: Tests fail silently or return None when mock returns None for futures/awaitables.

**Fix**: Configure conftest.py fixtures to have the chain mock return complete objects with all required fields.