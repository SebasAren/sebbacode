"""Memory extraction integration — wires session extraction into the L1/L2 layer.

This module is the bridge between the graph-level extraction step
(``sebba_code.nodes.extract.extract_session``) and the persistent memory layer
(``sebba_code.memory.layers``).

Flow
----
``extract_session`` calls ``run_extraction(updates, index_updates, rules)``:

    task_results[*].memory_updates
        ├── memory_updates ──→ MemoryLayer.write_l2()  → L2 files
        ├── index_updates   ──→ apply_index_updates()  → L0 _index.md
        └── new_rules       ──→ apply_new_rules()      → rules/

    L2 writes fire post_extraction_hook() asynchronously.
    The hook calls MemoryLayer.write_l1() via summarise_l2_to_l1().
    L1 is therefore only written via the hook — never directly by extraction.
"""

from __future__ import annotations

import logging
from typing import Any

from sebba_code.memory.hook import post_extraction_hook

logger = logging.getLogger("sebba_code")


def run_extraction(
    updates: list[dict],
    index_updates: list[dict],
    rules: list[dict],
    fire_hook: bool = True,
) -> list[dict]:
    """Run the full extraction pipeline.

    Parameters
    ----------
    updates:
        Raw memory_updates from task results.
        Each dict must have ``file`` and ``content`` keys.
    index_updates:
        L0 index entries (old_line / new_line pairs).
    rules:
        New rule files to write verbatim to rules/.
    fire_hook:
        If True (default), the async L1 summarisation hook is triggered.
        Set to False in tests to avoid side effects.

    Returns
    -------
    Combined index entries to pass to apply_index_updates().
    """
    # Import lazily to avoid circular imports
    from sebba_code.helpers.memory_ops import apply_index_updates, apply_new_rules
    from sebba_code.memory.layers import MemoryLayer

    layer = MemoryLayer()
    l2_entries: list[dict] = []

    # ── 1. Write L2 entries ──────────────────────────────────────────────
    for update in updates:
        action = update.get("action", "create")
        content = update.get("content", "")
        if not content.strip():
            continue

        # Index-only / rule-only actions are handled separately
        if action in ("update_index", "append_rules"):
            continue

        file_key = update.get("file", "session")
        topic = _topic_from_file(file_key)

        entry = layer.write_l2(content, topic)
        if entry:
            l2_entries.append({
                "content": content,
                "file": entry.file,
                "topic": topic,
            })

    # ── 2. Update L0 index ────────────────────────────────────────────────
    if index_updates:
        try:
            apply_index_updates(index_updates)
        except Exception:
            logger.warning("apply_index_updates failed", exc_info=True)

    # ── 3. Write rules verbatim ───────────────────────────────────────────
    if rules:
        try:
            apply_new_rules(rules)
        except Exception:
            logger.warning("apply_new_rules failed", exc_info=True)

    # ── 4. Fire async L1 summarisation hook ──────────────────────────────
    if fire_hook and l2_entries:
        post_extraction_hook(
            l2_entries,
            background=True,
        )

    return index_updates


def _topic_from_file(file_key: str) -> str:
    """Derive a short topic string from a memory file key.

    memory/architecture.md   → "architecture"
    memory/decisions/adr.md  → "decisions"
    """
    from pathlib import Path

    stem = Path(file_key).stem
    # If the key has multiple path components, use the parent dir as topic
    parts = Path(file_key).parts
    if len(parts) > 2:          # memory/decisions/2026-03-25.md → decisions
        topic = parts[1]
    else:
        topic = stem
    return topic or "session"
