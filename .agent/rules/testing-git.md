---
paths:
  - "tests/test_tools/test_git_commit.py"
  - ".git/hooks/pre-commit"
---
# Git Testing & Commit Rules

## Pre-commit Hook
- Hook MUST be kept under 1479 characters
- Validation includes: `.gitignore` patterns, README documentation consistency, codebase structure
- Hook execution runs automatically on `git commit`; any validation failure prevents commit

## Git Testing Approach
1. Create test file at `tests/test_tools/{tool_name}_git.py`
2. Include both **mocked subprocess** tests (isolated, fast) and **real Git execution** tests (integration)
3. Use `_make_state` helper for state initialization
4. Apply `tmp_agent_dir` pattern for file-based tests

## Shell Command Validation
- Validate all shell command arguments BEFORE execution
- Fix `cd: too many arguments`: use `shlex.split()` for subprocess calls
- Always validate working directory exists and is an absolute path
- Run pytest from repo root to avoid import path failures

## Test Coverage
- Target minimum 20 tests for comprehensive coverage
- Run with `--tb=short` for cleaner output
- Coverage should span unit-level (function behavior) and integration-level (end-to-end commit workflow)
