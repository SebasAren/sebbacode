---
topic: recursion-limit-formula
source_l2_key: manual
version: 1
created_at: 2026-03-26T00:00:00+00:00
summary_model: manual
---

LangGraph recursion limit: `100 + (max_iterations * 10)`. Base 100 covers initial setup and LLM inference overhead; per-iteration factor of 10 accounts for repeated roadmaps in state memory. Example: `max_iterations=10` yields limit of 200.

<!-- l2_preview -->
Recursion limit formula: 100 + (max_iterations * 10). Base 100 for setup, 10 per iteration.
