---
topic: testing
source_l2_key: consolidated
version: 2
created_at: 2026-03-28
summary_model: manual
---

# Testing Patterns

## Test Infrastructure

- **Fixtures**: `tmp_agent_dir` creates temporary `.agent/` directory; `_make_state` factory for `AgentState` dicts
- **Run location**: Always run `pytest` from repo root (not from subdirectories)
- **LLM mocking**: `mock_invoke_with_timeout` autouse fixture in `test_memory/conftest.py`
- **Integration tests**: Marked `@pytest.mark.integration`, require real LLM endpoint, excluded from default runs via `-m 'not integration'`

## Mocking Conventions

### Patch Targets
- Patch at **usage site** (`module_that_imports.Y`), NOT at definition site
- Example: `@patch("sebba_code.nodes.planning.get_llm")` not `@patch("sebba_code.llm.get_llm")`

### Mock Response Objects
- `invoke_with_timeout` mocks MUST return content with ≥10 words and ≥40 characters
- Return complete typed response objects with all required fields — never `None`
- Include proper `AIMessage` structure when mocking LLM responses
- For tool call mocks: provide full `tool_calls` list with proper `id`, `name`, `args`

### Config Testing
- Test config via environment variable manipulation (`monkeypatch` or `os.environ`)
- Don't rely solely on defaults — verify override behavior

## Git Testing

Hybrid approach combining:
1. **Mocked subprocess**: `@patch("sebba_code.helpers.git.subprocess.run")` for isolated unit tests
2. **Real Git execution**: Integration tests that actually run git commands
3. **Shell command handling**: `shlex.split()` for safe command parsing (fixes `cd` too-many-args issue)

## Key Test Files

| Test Area | File | Fixtures |
|-----------|------|----------|
| Memory layers | `tests/test_memory/` | `tmp_memory_root`, autouse mock |
| Planning nodes | `tests/test_nodes/test_planning.py` | `_make_state`, mock LLM |
| Dispatch/DAG | `tests/test_nodes/test_dispatch.py` | `_task()` factory |
| Git commit | `tests/test_tools/test_git_commit.py` | `tmp_agent_dir`, `_make_state` |
| Config | `tests/test_config.py` | `monkeypatch` for env vars |

## Debugging Tips

- `importing.py` must succeed before `pytest` can collect tests
- If tests fail on import: check for circular imports or missing `__init__.py`
- `max_iterations=1` in test state to avoid infinite planning loops

<!-- l2_preview -->
Consolidated from testing.md, debugging.md and their L2 directories.