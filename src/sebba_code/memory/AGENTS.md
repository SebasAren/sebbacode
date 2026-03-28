# Tiered Memory System

**Parent:** `AGENTS.md` (root)
**Score:** 10 — distinct domain

## OVERVIEW
Dual-tier L1/L2 storage with cheap-LLM summarization. Memory lives under `.agent/memory/`.

## TIER ARCHITECTURE

| Tier | Location | Token Budget | Purpose |
|------|----------|--------------|---------|
| **L0** | `.agent/memory/_index.md` | ~500 | Always loaded. One-liner summaries. |
| **L1** | `.agent/memory/architecture.md`, `conventions.md` | ~2000 each | On relevance. Consolidated summaries. |
| **L2** | `.agent/memory/<topic>/` | ~4000 each | On demand. Detailed entries with source. |

## PUBLIC API

```python
# MemoryLayer — read/write L1 and L2 files
MemoryLayer(agent_dir: Path)          # Initialize with .agent/ path
layer.read_l1(topic) → L1Summary       # Read L1 summary
layer.write_l1(summary: L1Summary)     # Write L1 summary
layer.read_l2(topic, key) → L2Entry    # Read L2 entry
layer.write_l2(entry: L2Entry)         # Write L2 entry
layer.list_l2(topic) → list[L2Entry]   # List L2 entries for topic

# Summarization — L2 → L1 condensation
summarise_l2_to_l1(l2_entry, cheap_llm) → L1Summary
summarise_topic_to_l1(topic, cheap_llm) → L1Summary

# Hook — async pipeline trigger
post_extraction_hook(l2_entries: list[L2EntryDict])  # Async L1 summarization
summarise_and_write(l2_entry)                        # Sync one-shot pipeline
```

## KEY CLASSES

```python
class L1Summary(TypedDict):
    file: str
    topic: str
    summary: str
    source_l2_key: str
    l2_preview: str
    created_at: str
    version: int
    summary_model: str

class L2Entry(TypedDict):
    content: str       # Full extracted content
    file: str          # Source file path
    topic: str         # Topic/category (e.g., "auth", "api")
```

## CONVENTIONS

- L2 entries stored as individual `.md` files under `.agent/memory/<topic>/`
- L1 summaries stored as `.md` files directly under `.agent/memory/`
- `content_hash` used for deduplication
- `topic_from_path` extracts topic from file path
- Async executor via `reset_executor()` / `close_executor()` cleanup

## TESTING

- `test_memory/conftest.py` provides `mock_invoke_with_timeout` as `autouse=True`
- `tmp_memory_root` fixture for temporary memory directory
- Integration tests require unmocking the fixture

## NOTES

- LLM summarization uses `invoke_with_timeout` with cheap model
- `post_extraction_hook` triggers async summarization after L2 writes
- Memory index (`_index.md`) is the L0 — always loaded first
- Agent reads L0 → decides which L1/L2 to load based on relevance
