---
topic: gate-baselines
source_l2_key: manual
version: 1
created_at: 2026-03-26T00:00:00+00:00
summary_model: manual
---

L2-to-L1 summarization uses a 50-character minimum content-length threshold. The post-extraction hook checks content length before triggering summarization via `summarize_to_l1`, preventing wasteful extraction of trivial L2 content.

<!-- l2_preview -->
L2->L1 summarization gated by 50-char minimum content length threshold.
