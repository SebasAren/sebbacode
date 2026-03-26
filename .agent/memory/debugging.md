---
topic: debugging
source_l2_key: manual
version: 1
created_at: 2026-03-26T00:00:00+00:00
summary_model: manual
---

Run pytest from repo root to avoid import path failures. Key test patterns: `tmp_agent_dir` fixture for `.agent/` directory structure, `_make_state` helper for consistent state creation, `unittest.mock` for LLM simulation. Set `max_iterations` high enough to avoid premature loop completion. When mocking `invoke_with_timeout`, the mock must return properly structured response objects with all required fields (not None).

<!-- l2_preview -->
Always run pytest from correct repo root. Key fixtures: tmp_agent_dir, _make_state, unittest.mock.
