---
paths:
  - "src/sebba_code/memory/**"
  - "src/sebba_code/nodes/extract.py"
  - "src/sebba_code/helpers/memory_ops.py"
  - "src/sebba_code/nodes/summarize.py"
---
# Memory Pipeline Rules

## Layer Separation
- Extraction writes to **L2 only**. Do NOT write directly to L1 from extraction code
- L1 is populated exclusively by the async condensation pipeline (`summarize_to_l1` node)
- Keep orthogonal concerns in separate modules: summarization logic in `summarize.py`, storage layer in `layers.py`

## Summarization Gating
- L2→L1 summarization gated by 50-character minimum content length threshold
- Only L2 content above threshold triggers L1 generation to avoid trivial summaries
- Content below threshold is copied verbatim to L1

## Write Locations
Memory writes are distributed across node implementations (context.py, rules.py, deepening.py), NOT centralized in `src/sebba_code/memory/`. The `memory/` directory contains only the storage layer.

## Extraction Flow
```
workers collect memory_updates in state
  → extract_session applies L2 writes via MemoryLayer.write_l2()
  → apply_index_updates() for L0
  → apply_new_rules() for rules/
  → summarize_to_l1 node condenses L2→L1 with cheap LLM
```
