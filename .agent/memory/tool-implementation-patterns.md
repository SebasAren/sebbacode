---
topic: tool-implementation-patterns
source_l2_key: manual
version: 1
created_at: 2026-03-26T00:00:00+00:00
summary_model: manual
---

New execution tools should follow `tools/code.py` pattern using subprocess for shell execution. Optional parameters (e.g. `files` in `git_commit`) reduce complexity while maintaining flexibility. Tool registration must be verified in both `get_all_tools()` (15 total) and `get_worker_tools()` (11 total) in `tools/__init__.py`. Schema validation tests should confirm required vs optional parameter behavior.

<!-- l2_preview -->
Follow tools/code.py pattern for new tools. Register in get_all_tools() and get_worker_tools().
