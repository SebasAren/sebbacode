"""Post-extraction hook: after L2 is written, trigger L1 summarisation asynchronously.

This module provides ``post_extraction_hook`` — the wiring point that lives
inside (or alongside) the extraction path in the worker graph.  When the
extraction step writes detailed memory to L2, this hook fires the cheap-LLM
summarisation step so L1 stays current without blocking the extraction itself.

Usage
-----
In the worker subgraph, after ``apply_memory_updates`` writes L2 content::

    from sebba_code.memory.hook import post_extraction_hook

    post_extraction_hook(
        l2_entries=[{"topic": "memory", "content": "...", "file": "memory/session.md"}],
        background=True,   # fire-and-forget via threading
    )

``background=True`` (the default) means the hook never blocks the extraction
pipeline and failures are swallowed with logging.
``background=False`` is useful in tests or synchronous pipelines where you want
the summarisation to complete before continuing.
"""

from __future__ import annotations

import logging
import threading
from collections import defaultdict
from concurrent.futures import Future, ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Optional

from sebba_code.memory.layers import (
    L1Summary,
    L2Entry,
    MemoryLayer,
    MemoryLayerConfig,
    content_hash,
)
from sebba_code.memory.summarize import summarise_l2_to_l1, summarise_topic_to_l1

logger = logging.getLogger("sebba_code")

# Shared thread pool so we don't spin up a new thread per hook call.
_executor: Optional[ThreadPoolExecutor] = None


def _get_executor() -> ThreadPoolExecutor:
    global _executor
    if _executor is None:
        _executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="summariser")
    return _executor


# ──────────────────────────────────────────────────────────────────────────────
# Public hook
# ──────────────────────────────────────────────────────────────────────────────


def post_extraction_hook(
    l2_entries: list[dict],
    *,
    topic: Optional[str] = None,
    background: bool = True,
    consolidate: bool = False,
    layer: Optional[MemoryLayer] = None,
    config: Optional[MemoryLayerConfig] = None,
) -> Optional[Future[list[L1Summary]]]:
    """Trigger L1 summarisation for L2 entries written during extraction.

    Parameters
    ----------
    l2_entries:
        List of dicts with keys ``content`` (str) and optionally ``file`` (str)
        and ``topic`` (str).  These represent the L2 items that were just
        written to disk.
    topic:
        Override topic name.  If not provided, derived from the first entry's
        file path or defaults to ``"session"``.
    background:
        If ``True`` (default), the summarisation is dispatched on a background
        thread and a ``Future`` is returned immediately.  If ``False``, the
        hook runs synchronously and blocks until all summaries are written.
    consolidate:
        If ``True``, all L2 entries are first concatenated into one big L2
        document and a single L1 summary is produced for the whole topic
        (via :func:`summarise_topic_to_l1`).  If ``False`` (default), each
        L2 entry gets its own L1 summary.
    layer:
        ``MemoryLayer`` instance.  Created lazily if omitted.
    config:
        Override for ``MemoryLayerConfig`` settings.

    Returns
    -------
    A ``concurrent.futures.Future[list[L1Summary]]`` when ``background=True``,
    or the actual ``list[L1Summary]`` when ``background=False``.
    Returns ``None`` immediately when the entry list is empty.

    The hook is idempotent: re-running with the same L2 content will not
    create duplicate L1 files (the version counter is incremented instead).
    """
    if not l2_entries:
        logger.debug("post_extraction_hook: no L2 entries provided, skipping")
        return None

    cfg = config or MemoryLayerConfig()
    ml = layer or MemoryLayer(config=cfg)

    # ── Build canonical L2Entry objects ──────────────────────────────────
    entries: list[L2Entry] = []
    resolved_topic = topic
    for i, entry_dict in enumerate(l2_entries):
        content = entry_dict.get("content", "")
        if not content or len(content) < cfg.min_l2_length_to_write:
            continue

        entry_topic = entry_dict.get("topic") or (
            Path(entry_dict.get("file", "")).stem if entry_dict.get("file") else ""
        )
        entry_topic = entry_topic or f"topic_{i}"
        resolved_topic = resolved_topic or entry_topic

        entry = L2Entry(
            key=content_hash(content),
            topic=entry_topic,
            content=content,
            file=entry_dict.get("file", f"{entry_topic}/{content_hash(content)}.md"),
            created_at=entry_dict.get("created_at", ""),
            version=1,
        )
        entries.append(entry)

    if not entries:
        logger.debug("post_extraction_hook: all entries too short, skipping")
        return None

    topic_for_summary = resolved_topic or "session"

    # ── Dispatch ─────────────────────────────────────────────────────────
    def _run():
        results: list[L1Summary] = []
        if consolidate:
            results.extend(
                summarise_topic_to_l1(topic_for_summary, layer=ml, config=cfg)
            )
        else:
            # Group entries by topic to avoid parallel writes to the same L1 file.
            # Each topic produces exactly one consolidated L1 summary from all its L2 entries.
            by_topic: dict[str, list[L2Entry]] = defaultdict(list)
            for entry in entries:
                by_topic[entry.topic].append(entry)

            for t, topic_entries in by_topic.items():
                try:
                    if len(topic_entries) == 1:
                        result = summarise_l2_to_l1(
                            topic_entries[0], layer=ml, config=cfg
                        )
                        if result:
                            results.append(result)
                    else:
                        consolidated = summarise_topic_to_l1(t, layer=ml, config=cfg)
                        results.extend(consolidated)
                except Exception as exc:
                    logger.warning("L1 summarisation failed for topic=%s: %s", t, exc)
        return results

    if background:
        return _get_executor().submit(_run)
    else:
        return _run()


# ──────────────────────────────────────────────────────────────────────────────
# Synchronous convenience wrappers (useful in tests and REPL)
# ──────────────────────────────────────────────────────────────────────────────


def summarise_and_write(
    content: str,
    topic: str,
    *,
    layer: Optional[MemoryLayer] = None,
    config: Optional[MemoryLayerConfig] = None,
) -> Optional[L1Summary]:
    """Convenience: write L2 then immediately summarise to L1 (synchronous).

    This is a single-shot helper for cases where you have one piece of content
    and want the full L2→L1 pipeline in one call.

    Returns the ``L1Summary`` or ``None`` if the content was skipped.
    """
    cfg = config or MemoryLayerConfig()
    ml = layer or MemoryLayer(config=cfg)

    entry = ml.write_l2(content, topic)
    if entry is None:
        return None
    return summarise_l2_to_l1(entry, layer=ml, config=cfg)


def close_executor() -> None:
    """Shut down the background thread pool. Call at process exit."""
    global _executor
    if _executor is not None:
        _executor.shutdown(wait=False)
        _executor = None


def reset_executor() -> None:
    """Reset the global executor (for use in tests to prevent state bleed)."""
    global _executor
    close_executor()
