---
topic: Testing
source_l2_key: f27f41521fae070e
version: 1
created_at: 2026-03-26T19:25:07.109711+00:00
summary_model: qwen3-5-9b
---

Git commit testing at `tests/test_tools/test_git_commit.py` combines mocked subprocess and real Git execution for 21 tests. Fix `cd: too many arguments` by validating arguments with `shlex.split()` before calls. Use `tmp_agent_dir`, `_make_state`, and `unittest.mock` with complete mock responses. Run pytest from repo root after verifying imports. Use `monkeypatch` or `os.environ` for environments. Escape commands, verify paths, and ensure absolute directories.

<!-- l2_preview -->
## Git Commit Testing Integration Pattern

### Core Principle
Git commit testing requires a hybrid approach combining mocked subprocess calls for isolation with real Git execution for integration verification.

### Implementation Details

**File Location:** `tests/test_tools/test_git_commit.py`

**T