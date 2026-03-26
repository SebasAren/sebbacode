---
paths:
  - "tests/test_tools/test_git_commit.py"
---
## Git Commit Testing Patterns

### Testing Approach
1. Create test file at `tests/test_tools/{tool_name}_git.py`
2. Include both mocked subprocess tests (isolated) and real Git execution workflows (integration)
3. Use `_make_state` helper function for state initialization
4. Apply `tmp_agent_dir` pattern for file-based tests

### Shell Command Validation
- Validate all shell command arguments BEFORE execution
- Issue: `cd: too many arguments` indicates improper argument parsing
- Solution: Use proper argument parsing (shlex.split) for subprocess calls
- Always validate working directory exists and is an absolute path

### Mock Configuration
- Mock objects MUST return complete response objects with all required fields
- Do not return None - mocks must simulate complete execution
- Patch at usage site: `module_that_imports.func`, not `module.func`

### Test Validation
- Verify imports succeed before pytest execution
- Run pytest from repo root to avoid import path failures
- Run with `--tb=short` for cleaner output
- Target minimum 20 tests for comprehensive coverage

### Integration Requirements
- Test both mocked scenarios (safe, fast)
- Test real Git execution (actual integration)
- Coverage should span unit-level (function behavior) and integration-level (end-to-end commit workflow)