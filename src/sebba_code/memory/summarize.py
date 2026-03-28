"""L2 → L1 summarisation using the cheap LLM.

This module is responsible for the "condensation step": taking detailed L2
memory entries and producing concise L1 summaries via a fast/cheap model.

Design principles
-----------------
- **Non-blocking**: summarisation failures are logged but never crash or
  block the caller. The L2 content is always preserved.
- **Idempotent**: calling ``summarise_l2_to_l1`` on the same L2 entry twice
  will produce the same result (same version) — no duplicate summaries.
- **Versioned**: each L1 file carries a ``version`` counter so callers can
  detect stale summaries.
- **Retry with backoff**: transient cheap-LLM timeouts are retried up to
  ``config.max_summarization_retries`` times before giving up.
"""

from __future__ import annotations

import logging
import time
from dataclasses import replace
from datetime import datetime, UTC
from pathlib import Path
from typing import Optional

from sebba_code.llm import get_cheap_llm, invoke_with_timeout
from sebba_code.memory.layers import (
    L1Summary,
    L2Entry,
    MemoryLayer,
    MemoryLayerConfig,
    content_hash,
    topic_from_path,
)

logger = logging.getLogger("sebba_code")

# ──────────────────────────────────────────────────────────────────────────────
# Prompt templates
# ──────────────────────────────────────────────────────────────────────────────

_SUMMARISE_SYSTEM_PROMPT = """You are a technical knowledge condensation engine.
Produce a concise, accurate, and self-contained summary of the provided memory entry.

Rules:
- Preserve ALL specific identifiers: filenames, function names, class names, module paths, and variable names verbatim.
- Preserve ALL architectural decisions and the reasoning behind them.
- Preserve ALL error conditions, edge cases, and gotchas discovered.
- Remove conversational filler, repetition, and boilerplate context.
- Output ONLY the summary text — no preamble, no closing remarks.
- Target roughly 40-60% of the original length. Prefer losing minor details over losing identifiers.
- If the source is already under 100 words, produce a single concise sentence.
- Structure with bullet points when multiple distinct facts are present.
""".strip()

_SUMMARISE_USER_PROMPT = """## Memory Entry to Summarise

Topic: {topic}
Source file: {source_file}

---
{content}
---

Write a concise summary following the rules above."""


# ──────────────────────────────────────────────────────────────────────────────
# Public API
# ──────────────────────────────────────────────────────────────────────────────


def summarise_l2_to_l1(
    l2_entry: L2Entry,
    layer: Optional[MemoryLayer] = None,
    config: Optional[MemoryLayerConfig] = None,
    timeout_seconds: int = 30,
) -> Optional[L1Summary]:
    """Summarise a single L2 entry and write the resulting L1 file.

    Parameters
    ----------
    l2_entry:
        The detailed L2 memory entry to condense.
    layer:
        ``MemoryLayer`` instance used for L1 writes.  If not provided,
        a default instance is created.
    config:
        Override for ``MemoryLayerConfig`` settings (e.g. retry counts).
    timeout_seconds:
        Hard timeout for the cheap LLM call (default 30 s).

    Returns
    -------
    The written ``L1Summary``, or ``None`` if the entry was skipped
    (too short) or all retries failed.

    The L2 entry is never modified.  The L1 file is written atomically
    via ``MemoryLayer.write_l1``.
    """
    cfg = config or MemoryLayerConfig()
    layer = layer or MemoryLayer(config=cfg)

    # ── Guard: skip trivially short content ──────────────────────────────
    content = l2_entry.content
    if len(content) < cfg.min_l2_length_for_summary:
        logger.debug(
            "Skipping summarisation for key=%s: only %d chars (< %d minimum)",
            l2_entry.key,
            len(content),
            cfg.min_l2_length_for_summary,
        )
        # Still write a verbatim L1 for short content — no LLM needed.
        summary_text = content.strip()
    else:
        # ── Guard: truncate oversized content before sending to cheap LLM ──
        if len(content) > cfg.max_l2_length_for_summary:
            logger.warning(
                "L2 content for key=%s is %d chars (limit %d); truncating for summarisation.",
                l2_entry.key,
                len(content),
                cfg.max_l2_length_for_summary,
            )
            content = content[: cfg.max_l2_length_for_summary]

        # ── Call cheap LLM with retry ──────────────────────────────────────
        summary_text = _call_summarise_with_retry(
            topic=l2_entry.topic,
            source_file=l2_entry.file,
            content=content,
            cfg=cfg,
            timeout_seconds=timeout_seconds,
        )
        if summary_text is None:
            logger.error(
                "Summarisation failed permanently for key=%s after %d retries",
                l2_entry.key,
                cfg.max_summarization_retries,
            )
            return None

    # ── Build L1 file path ────────────────────────────────────────────────
    # Use the same stem as the L2 directory so L1 "concepts/caching.md"
    # corresponds to L2 "concepts/caching/*.md".
    l1_rel = f"{l2_entry.topic}.md"

    # Check if L1 already exists and bump version
    existing = layer.read_l1(l1_rel)
    version = (existing.version + 1) if existing else 1

    model_name = _get_model_name()

    summary = L1Summary(
        file=l1_rel,
        topic=l2_entry.topic,
        summary=summary_text,
        source_l2_key=l2_entry.key,
        l2_preview=l2_entry.content[:300].strip(),
        created_at=datetime.now(UTC).isoformat(),
        version=version,
        summary_model=model_name,
    )

    layer.write_l1(summary)
    _sync_l0_index(layer.memory_root, l2_entry.topic, summary_text)
    return summary


def summarise_topic_to_l1(
    topic: str,
    layer: Optional[MemoryLayer] = None,
    config: Optional[MemoryLayerConfig] = None,
    timeout_seconds: int = 30,
) -> list[L1Summary]:
    """Load all L2 entries for *topic* and produce a single consolidated L1.

    Use this when you want one summary that covers all L2 content under a
    topic rather than one summary per L2 entry.
    """
    layer = layer or MemoryLayer(config=config or MemoryLayerConfig())
    cfg = config or MemoryLayerConfig()

    all_content = layer.l2_content_for_topic(topic)
    if not all_content:
        logger.debug("No L2 entries found for topic=%s", topic)
        return []

    # Treat the concatenated content as a single synthetic L2 entry
    synthetic = L2Entry(
        key=content_hash(all_content),
        topic=topic,
        content=all_content,
        file=f"{topic}/__consolidated__.md",
        created_at=datetime.now(UTC).isoformat(),
        version=1,
    )

    result = summarise_l2_to_l1(
        synthetic,
        layer=layer,
        config=cfg,
        timeout_seconds=timeout_seconds,
    )
    return [result] if result else []


# ──────────────────────────────────────────────────────────────────────────────
# Internal helpers
# ──────────────────────────────────────────────────────────────────────────────


def _call_summarise_with_retry(
    topic: str,
    source_file: str,
    content: str,
    cfg: MemoryLayerConfig,
    timeout_seconds: int,
) -> Optional[str]:
    """Call the cheap LLM summariser with exponential-backoff retry."""
    model = get_cheap_llm()

    user_prompt = _SUMMARISE_USER_PROMPT.format(
        topic=topic,
        source_file=source_file,
        content=content,
    )

    for attempt in range(1 + cfg.max_summarization_retries):
        try:
            response = invoke_with_timeout(
                model,
                [("system", _SUMMARISE_SYSTEM_PROMPT), ("user", user_prompt)],
                timeout_seconds=timeout_seconds,
            )
            text = _strip_markdown_code_fences(response.content)
            if len(text) > len(content):
                logger.warning(
                    "Summarisation for topic=%s expanded content (%d > %d chars); "
                    "using original content as L1 summary.",
                    topic,
                    len(text),
                    len(content),
                )
                return content.strip()
            if _is_valid_summary(text, min_words=10):
                return text
            logger.warning(
                "Summarisation output for topic=%s looks invalid (too short / "
                "empty); attempt %d/%d",
                topic,
                attempt + 1,
                1 + cfg.max_summarization_retries,
            )
        except Exception as exc:
            logger.warning(
                "Summarisation call failed for topic=%s: %s; attempt %d/%d",
                topic,
                exc,
                attempt + 1,
                1 + cfg.max_summarization_retries,
            )

        if attempt < cfg.max_summarization_retries:
            delay = cfg.summarization_retry_base_delay * (2**attempt)
            logger.debug("Retrying summarisation in %.1f seconds…", delay)
            time.sleep(delay)

    return None


def _strip_markdown_code_fences(text: str) -> str:
    """Remove leading/trailing markdown code fences from LLM output."""
    lines = text.splitlines()
    while lines and lines[0].strip() in ("```", "```markdown", "```text"):
        lines.pop(0)
    while lines and lines[-1].strip() in ("```", "```markdown", "```text"):
        lines.pop()
    return "\n".join(lines).strip()


def _is_valid_summary(text: str, min_words: int = 10) -> bool:
    """Return True when the summary looks like real content, not garbage."""
    if not text or len(text) < 40:
        return False
    words = text.split()
    if len(words) < min_words:
        return False
    # Reject obvious LLM filler patterns that carry no information
    filler_phrases = [
        "this document describes",
        "the above content",
        "in summary,",
        "to summarize,",
        "as mentioned above",
    ]
    lower = text.lower()
    if any(p in lower for p in filler_phrases) and len(words) < 30:
        return False
    return True


def _sync_l0_index(memory_root: Path, topic: str, summary_text: str) -> None:
    """Ensure the topic has an entry in the L0 _index.md file."""
    index_path = memory_root / "_index.md"
    if not index_path.exists():
        return

    content = index_path.read_text()
    # Check if topic already has a bullet in the index
    topic_header = f"**{topic}**"
    if topic_header in content:
        return

    # Extract a one-liner from the summary (first sentence, max 120 chars)
    first_sentence = summary_text.split(".")[0].strip()
    if len(first_sentence) > 120:
        first_sentence = first_sentence[:117] + "..."
    new_line = f"- **{topic}**: {first_sentence}"

    content = content.rstrip() + "\n" + new_line + "\n"
    index_path.write_text(content)
    logger.info("L0 index updated with topic=%s", topic)


def _get_model_name() -> str:
    """Return the cheap model name for recording in L1 metadata."""
    try:
        from sebba_code.llm import _cheap_llm

        # Access the internal model name via langchain's model instance
        return getattr(_cheap_llm, "model", "") or "unknown"
    except Exception:
        return "unknown"
