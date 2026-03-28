---
topic: memory-pipeline
source_l2_key: consolidated
version: 2
created_at: 2026-03-28
summary_model: manual
---

# Memory Pipeline

## Tier Architecture

| Tier | Location | Token Budget | When Loaded |
|------|----------|--------------|-------------|
| L0 | `_index.md` | ~500 | Always |
| L1 | `<topic>.md` with frontmatter | ~2000 each | On relevance |
| L2 | `<topic>/*.md` | ~4000 each | On demand |

## Write Flow

1. **Extraction** (`extract_session` node): Workers collect `memory_updates` in state
2. **L2 Write** (`apply_memory_updates`): Writes detailed content to L2 via `MemoryLayer.write_l2()`
3. **L0 Update** (`apply_index_updates`): Appends/replaces lines in `_index.md`
4. **Rules Write** (`apply_new_rules`): Writes path-scoped rules verbatim
5. **L1 Condensation** (`summarize_to_l1` node): Cheap LLM summarizes L2 → L1, gated by 50-char minimum

**Critical**: Extraction writes to L2 ONLY. L1 is populated exclusively by the async condensation pipeline. Never write L1 directly from extraction code.

## L2 Write Rules

- Content deduplication via `content_hash()` (SHA-256, first 16 hex chars)
- Files below `min_l2_length_to_write` (50 chars) are skipped entirely
- Files above `max_l2_length_to_write` (6000 chars) are truncated
- Max 20 L2 entries per topic directory; oldest evicted when exceeded
- Suggested name from file stem, falls back to content hash

## L1 Summarization Gate

L2→L1 summarization only fires when content length > `min_l2_length_for_summary` (400 chars). Content below this threshold is copied verbatim to L1.

## Memory Write Locations

Memory writes are distributed across node implementations, NOT centralized in `src/sebba_code/memory/`:
- `nodes/context.py` — contextual memory during deepening
- `nodes/rules.py` — rule-based memory during matching
- `nodes/deepening.py` — deep-dive memory during context selection

The `memory/` directory contains only the storage layer (`layers.py`, `extraction.py`, `hook.py`).

## Topic Derivation

`_topic_from_file()` uses the directory part of the file path:
- `"architecture/example.md"` → topic `"architecture"`
- `"testing.md"` → topic `"testing"` (stem fallback)

## Session Summaries

After extraction, session summaries are written to `.agent/sessions/{date}.md` with:
- Tasks completed count
- Per-task: summary, what was done, decisions made, files touched

<!-- l2_preview -->
Consolidated from gate-baselines.md, patterns.md, recursion-limit-formula.md, git-hooks.md and their L2 directories.
