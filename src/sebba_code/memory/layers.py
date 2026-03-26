"""L1/L2 memory layer — persistent storage for summaries (L1) and detailed content (L2)."""

from __future__ import annotations

import hashlib
import logging
import shutil
from dataclasses import dataclass
from datetime import datetime, UTC
from pathlib import Path
from typing import Optional

from sebba_code.constants import get_agent_dir

logger = logging.getLogger("sebba_code")


# ──────────────────────────────────────────────────────────────────────────────
# Config
# ──────────────────────────────────────────────────────────────────────────────

@dataclass
class MemoryLayerConfig:
    """Configuration for L1/L2 memory layers."""

    # Minimum L2 content length (chars) before L1 summarisation is triggered.
    # Content shorter than this is copied verbatim to L1.
    min_l2_length_for_summary: int = 400

    # Minimum L2 content length (chars) before L2 is even written.
    # Content shorter than this is skipped entirely.
    min_l2_length_to_write: int = 50

    # Max L2 content length (chars). Content longer than this is truncated
    # before summarisation to avoid excessive token usage on cheap LLM.
    max_l2_length_for_summary: int = 8000

    # Maximum number of retry attempts when L1 summarisation fails.
    max_summarization_retries: int = 2

    # Base backoff delay (seconds) between retry attempts.
    summarization_retry_base_delay: float = 2.0


# ──────────────────────────────────────────────────────────────────────────────
# L1 / L2 record containers
# ──────────────────────────────────────────────────────────────────────────────

@dataclass
class L1Summary:
    """A condensed summary stored at L1 (one per L2 group)."""

    file: str           # relative path within memory/  e.g. "concepts/caching.md"
    topic: str          # short human-readable topic derived from the path
    summary: str        # the LLM-generated summary text
    source_l2_key: str  # which L2 entry this summarises
    l2_preview: str     # first ~200 chars of the original L2 content
    created_at: str     # ISO-8601 timestamp
    version: int = 1    # monotonically increasing on re-summarisation
    summary_model: str = ""  # model used for summarisation (for audit)

    def to_dict(self) -> dict:
        return {
            "file": self.file,
            "topic": self.topic,
            "summary": self.summary,
            "source_l2_key": self.source_l2_key,
            "l2_preview": self.l2_preview,
            "created_at": self.created_at,
            "version": self.version,
            "summary_model": self.summary_model,
        }


@dataclass
class L2Entry:
    """A detailed memory entry stored at L2 (raw extraction output)."""

    key: str          # deterministic key derived from content (prevents duplicates)
    topic: str         # short topic, usually derived from the containing directory
    content: str       # full detailed content
    file: str          # relative path where this entry lives on disk
    created_at: str   # ISO-8601 timestamp
    version: int = 1  # incremented on each update to the same key

    def to_dict(self) -> dict:
        return {
            "key": self.key,
            "topic": self.topic,
            "content": self.content,
            "file": self.file,
            "created_at": self.created_at,
            "version": self.version,
        }


# ──────────────────────────────────────────────────────────────────────────────
# Content hashing utilities
# ──────────────────────────────────────────────────────────────────────────────

def content_hash(content: str) -> str:
    """Return a short hex digest of the content (used as a stable L2 key)."""
    return hashlib.sha256(content.encode()).hexdigest()[:16]


def topic_from_path(relative_path: str) -> str:
    """Derive a short human-readable topic from a memory file path."""
    stem = Path(relative_path).stem
    # Replace underscores / hyphens with spaces and title-case
    return stem.replace("_", " ").replace("-", " ").title()


# ──────────────────────────────────────────────────────────────────────────────
# Core storage class
# ──────────────────────────────────────────────────────────────────────────────

class MemoryLayer:
    """Dual-tier memory: L2 stores detailed extractions, L1 stores summaries.

    The two tiers are both stored on disk under::

        .agent/memory/
            _index.md          ← L0: master index (written by helpers/memory_ops)
            <topic>.md         ← L1: summary per topic (this module)
            <topic>/
                *.md           ← L2: detailed entries (this module)

    L2 entries are written first by extraction hooks; L1 summaries are then
    generated asynchronously from L2 content using the cheap LLM.
    """

    def __init__(
        self,
        memory_root: Optional[Path] = None,
        config: Optional[MemoryLayerConfig] = None,
    ):
        self.memory_root = memory_root or (get_agent_dir() / "memory")
        self.config = config or MemoryLayerConfig()

    # ── L2 operations ──────────────────────────────────────────────────────

    def write_l2(
        self,
        content: str,
        topic: str,
        *,
        skip_if_short: bool = True,
    ) -> Optional[L2Entry]:
        """Write a detailed L2 entry to disk.

        Returns an ``L2Entry`` if the entry was written, or ``None`` if it was
        skipped (content too short or already exists unchanged).

        Idempotent: writing the same content twice will not create duplicates.
        """
        if skip_if_short and len(content) < self.config.min_l2_length_to_write:
            logger.debug(
                "L2 write skipped: content too short (%d < %d chars)",
                len(content), self.config.min_l2_length_to_write,
            )
            return None

        key = content_hash(content)
        l2_dir = self.memory_root / topic
        l2_dir.mkdir(parents=True, exist_ok=True)

        # Check for an identical entry already on disk (idempotency guard)
        candidate_file = l2_dir / f"{key}.md"
        if candidate_file.exists():
            existing = candidate_file.read_text()
            if existing.strip() == content.strip():
                logger.debug("L2 entry already exists for key=%s, skipping", key)
                return None

        file_path = candidate_file
        file_path.write_text(content)

        entry = L2Entry(
            key=key,
            topic=topic,
            content=content,
            file=str(file_path.relative_to(self.memory_root)),
            created_at=datetime.now(UTC).isoformat(),
            version=1,
        )
        logger.info("L2 written: %s (key=%s, topic=%s)", file_path.name, key, topic)
        return entry

    def read_l2(self, topic: str) -> list[L2Entry]:
        """Load all L2 entries for a given topic."""
        l2_dir = self.memory_root / topic
        if not l2_dir.is_dir():
            return []

        entries = []
        for md_file in sorted(l2_dir.glob("*.md")):
            try:
                content = md_file.read_text()
                entries.append(
                    L2Entry(
                        key=md_file.stem,
                        topic=topic,
                        content=content,
                        file=str(md_file.relative_to(self.memory_root)),
                        created_at=datetime.now(UTC).isoformat(),
                        version=1,
                    )
                )
            except Exception as exc:
                logger.warning("Failed to read L2 file %s: %s", md_file, exc)
        return entries

    def l2_content_for_topic(self, topic: str) -> str:
        """Return all L2 entries for a topic concatenated together."""
        entries = self.read_l2(topic)
        if not entries:
            return ""
        return "\n\n---\n\n".join(e.content for e in entries)

    # ── L1 operations ─────────────────────────────────────────────────────

    def write_l1(self, summary: L1Summary) -> Path:
        """Write a single L1 summary file to disk.

        Returns the path of the written file.
        """
        l1_file = self.memory_root / summary.file
        l1_file.parent.mkdir(parents=True, exist_ok=True)

        # Include minimal front-matter so other tools can parse it
        lines = [
            "---",
            f"topic: {summary.topic}",
            f"source_l2_key: {summary.source_l2_key}",
            f"version: {summary.version}",
            f"created_at: {summary.created_at}",
            f"summary_model: {summary.summary_model}",
            "---",
            "",
            summary.summary,
            "",
            "<!-- l2_preview -->",
            summary.l2_preview,
        ]
        l1_file.write_text("\n".join(lines))
        logger.info("L1 written: %s (version=%d)", l1_file.name, summary.version)
        return l1_file

    def read_l1(self, relative_path: str) -> Optional[L1Summary]:
        """Read an L1 summary file back into an ``L1Summary``."""
        l1_file = self.memory_root / relative_path
        if not l1_file.is_file():
            return None

        text = l1_file.read_text()
        # Strip front-matter (--- ... ---)
        if text.startswith("---"):
            parts = text.split("---", 2)
            if len(parts) >= 3:
                frontmatter = parts[1]
                body = parts[2]
                meta = {}
                for line in frontmatter.strip().splitlines():
                    if ":" in line:
                        k, v = line.split(":", 1)
                        meta[k.strip()] = v.strip()
                # content after <!-- l2_preview -->
                if "<!-- l2_preview -->" in body:
                    summary_text, _, preview_part = body.partition("<!-- l2_preview -->")
                    preview = preview_part.strip()
                else:
                    summary_text = body.strip()
                    preview = ""

                return L1Summary(
                    file=relative_path,
                    topic=meta.get("topic", ""),
                    summary=summary_text.strip(),
                    source_l2_key=meta.get("source_l2_key", ""),
                    l2_preview=preview,
                    created_at=meta.get("created_at", ""),
                    version=int(meta.get("version", 1)),
                    summary_model=meta.get("summary_model", ""),
                )

        # Fallback: treat whole file as summary
        return L1Summary(
            file=relative_path,
            topic=topic_from_path(relative_path),
            summary=text.strip(),
            source_l2_key="",
            l2_preview="",
            created_at="",
            version=1,
        )

    def l1_files_for_topic(self, topic: str) -> list[Path]:
        """List all L1 files matching a topic (same stem as L2 directory)."""
        candidates = [
            self.memory_root / f"{topic}.md",
        ]
        return [f for f in candidates if f.is_file()]

    # ── Cleanup ───────────────────────────────────────────────────────────

    def purge_l2_for_topic(self, topic: str) -> int:
        """Remove all L2 entries for a topic. Returns count of files removed."""
        l2_dir = self.memory_root / topic
        if not l2_dir.is_dir():
            return 0
        count = len(list(l2_dir.glob("*.md")))
        shutil.rmtree(l2_dir)
        logger.info("Purged %d L2 entries for topic=%s", count, topic)
        return count
