---
topic: patterns
source_l2_key: manual
version: 1
created_at: 2026-03-26T00:00:00+00:00
summary_model: manual
---

When todo titles and descriptions diverge, prefer the todo title as source of truth. Post-extraction hooks fire in `src/sebba_code/nodes/extract.py` after L2 writes for side effects (summarization, indexing). Tests should cover sync/async flows, hook timing, and threshold logic.

<!-- l2_preview -->
Todo titles are source of truth over descriptions. Post-extraction hooks fire after L2 writes.
