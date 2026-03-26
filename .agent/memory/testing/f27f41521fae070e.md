## Git Commit Testing Integration Pattern

### Core Principle
Git commit testing requires a hybrid approach combining mocked subprocess calls for isolation with real Git execution for integration verification.

### Implementation Details

**File Location:** `tests/test_tools/test_git_commit.py`

**Test Coverage Requirements:**
- 21 total tests covering unit and integration scenarios
- Mocked subprocess tests for isolated behavior verification
- Real Git execution workflows for integration validation

**Shell Command Error Handling:**
- Issue: `cd: too many arguments` occurs when command execution paths are improperly formatted
- Resolution: Validate command arguments before wrapping in subprocess calls
- Pattern: Use `shlex.split()` or equivalent to parse and validate arguments

**Test Structure Pattern:**
1. Create test directory with `tmp_agent_dir` pattern for file operations
2. Use `_make_state` helper for state initialization (check existing memory)
3. Apply `unittest.mock` for isolation
4. Configure mocks to return complete response objects (not None) per mock-response-objects.md rule
5. Execute command validation
6. Verify subprocess handling

**Validation Approach:**
- Run pytest from correct repo root to avoid import path failures (see debugging/test-execution.md)
- Test sequence: (1) verify import succeeds before running tests, (2) execute pytest suite

**Environment Variables:**
- Use `monkeypatch` or `os.environ` manipulation to test configuration options (per config-testing.md rule)

**Known Constraints:**
- Shell commands must be properly escaped/quoted
- Command paths must be valid and exist before execution
- Working directory must be absolute or correctly resolved

### Memory Index Reference
When encountering shell command errors in tests, check for argument count issues first before adding stdout/stderr capturing.