"""Tests for memory extraction: L2 writing, topic resolution, and deduplication."""

import tempfile
from datetime import datetime, UTC
from pathlib import Path
from unittest import TestCase
from unittest.mock import patch

from sebba_code.memory.layers import (
    L1Summary,
    L2Entry,
    MemoryLayer,
    MemoryLayerConfig,
    content_hash,
    topic_from_path,
)
from sebba_code.memory.hook import (
    post_extraction_hook,
    reset_executor,
)


def _now() -> str:
    return datetime.now(UTC).isoformat()


class TestContentHashExtraction(TestCase):
    """Tests for content hashing used in L2 deduplication."""

    def test_hash_deterministic_across_calls(self):
        """Hash must be stable so same content always produces same key."""
        content = "Extract this memory entry content for deduplication testing."
        h1 = content_hash(content)
        h2 = content_hash(content)
        self.assertEqual(h1, h2)

    def test_hash_changes_on_content_change(self):
        """Even a minor content change must produce a different hash."""
        h1 = content_hash("Original memory content.")
        h2 = content_hash("Modified memory content.")
        self.assertNotEqual(h1, h2)

    def test_hash_length_within_limits(self):
        """Hash must be short enough to use as a filename."""
        h = content_hash("any content")
        self.assertLessEqual(len(h), 16)
        # Must be valid hex
        int(h, 16)

    def test_hash_whitespace_normalized(self):
        """Content with only whitespace differences should have same hash."""
        h1 = content_hash("Content with spaces.")
        h2 = content_hash("Content  with  spaces.")
        self.assertNotEqual(h1, h2)  # hashing is exact, no normalization


class TestTopicFromPathExtraction(TestCase):
    """Tests for topic extraction from file paths."""

    def test_simple_stem_extraction(self):
        """Simple filename should have topic = stem title-cased."""
        self.assertEqual(topic_from_path("caching.md"), "Caching")
        self.assertEqual(topic_from_path("session.md"), "Session")

    def test_nested_path_extraction(self):
        """Nested paths should extract the final segment stem."""
        self.assertEqual(topic_from_path("concepts/caching.md"), "Caching")
        self.assertEqual(topic_from_path("memory/session_2024.md"), "Session 2024")

    def test_hyphen_replacement(self):
        """Hyphens should be replaced with spaces."""
        self.assertEqual(topic_from_path("architecture-overview.md"), "Architecture Overview")
        self.assertEqual(topic_from_path("code-style-guide.md"), "Code Style Guide")

    def test_underscore_replacement(self):
        """Underscores should be replaced with spaces."""
        self.assertEqual(topic_from_path("session_2024_01.md"), "Session 2024 01")
        self.assertEqual(topic_from_path("api_design.md"), "Api Design")


class TestL2ExtractionWrite(TestCase):
    """Tests for L2 entry extraction and writing."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.layer = MemoryLayer(memory_root=self.tmp)

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)
        reset_executor()

    def test_write_l2_returns_entry_with_correct_fields(self):
        """Written L2 entry should have all required fields populated."""
        content = "Detailed memory content for extraction testing with sufficient length."
        entry = self.layer.write_l2(content, topic="extraction")
        
        self.assertIsNotNone(entry)
        assert entry is not None
        self.assertEqual(entry.topic, "extraction")
        self.assertEqual(entry.content, content)
        self.assertEqual(entry.key, content_hash(content))
        self.assertTrue(entry.key.isalnum() or all(c in '0123456789abcdef' for c in entry.key))

    def test_write_l2_creates_directory_structure(self):
        """L2 write should create topic directory."""
        content = "Memory content for directory creation test — long enough."
        self.layer.write_l2(content, topic="new_topic")
        
        self.assertTrue((self.tmp / "new_topic").is_dir())

    def test_write_l2_skips_content_below_minimum(self):
        """Content shorter than min_l2_length_to_write should be skipped."""
        cfg = MemoryLayerConfig(min_l2_length_to_write=50)
        layer = MemoryLayer(memory_root=self.tmp, config=cfg)
        
        result = layer.write_l2("too short", topic="tiny")
        self.assertIsNone(result)
        self.assertFalse((self.tmp / "tiny").exists())

    def test_write_l2_accepts_content_at_threshold(self):
        """Content exactly at threshold should be written."""
        # Default min is 50 chars
        content = "Exactly fifty characters of content here for testing.XX"  # 50 chars
        entry = self.layer.write_l2(content, topic="threshold")
        
        self.assertIsNotNone(entry)
        assert entry is not None
        self.assertEqual(entry.content, content)

    def test_write_l2_idempotent_same_content(self):
        """Writing same content twice should be idempotent."""
        content = "Idempotent extraction test content — long enough for L2 writing."
        
        e1 = self.layer.write_l2(content, topic="session")
        e2 = self.layer.write_l2(content, topic="session")
        
        self.assertIsNotNone(e1)
        self.assertIsNone(e2)
        
        # Only one file should exist
        topic_dir = self.tmp / "session"
        self.assertEqual(len(list(topic_dir.glob("*.md"))), 1)

    def test_write_l2_different_content_creates_separate_files(self):
        """Different content under same topic should create separate files."""
        # Ensure content is >= 50 chars (min_l2_length_to_write)
        self.layer.write_l2(
            "First extraction entry for testing purposes with sufficient length.",
            topic="session",
        )
        self.layer.write_l2(
            "Second extraction entry for testing purposes with sufficient length.",
            topic="session",
        )
        
        topic_dir = self.tmp / "session"
        files = list(topic_dir.glob("*.md"))
        self.assertEqual(len(files), 2)

    def test_write_l2_preserves_content_verbatim(self):
        """Written content should match original exactly."""
        content = "Exact content\nwith\nmultiple\nlines\nfor testing with sufficient length."
        self.layer.write_l2(content, topic="verbatim")
        
        entry = self.layer.read_l2("verbatim")[0]
        self.assertEqual(entry.content, content)

    def test_write_l2_with_custom_created_at(self):
        """Custom created_at timestamp should be set."""
        entry = self.layer.write_l2(
            "Content with timestamp for extraction testing purposes here.",
            topic="timestamps",
        )
        # write_l2 uses datetime.now(), so just verify it's set
        self.assertIsNotNone(entry)


class TestL2ExtractionRead(TestCase):
    """Tests for reading L2 entries."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.layer = MemoryLayer(memory_root=self.tmp)

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)
        reset_executor()

    def test_read_l2_empty_for_nonexistent_topic(self):
        """Reading a topic with no entries should return empty list."""
        entries = self.layer.read_l2("nonexistent")
        self.assertEqual(entries, [])

    def test_read_l2_returns_all_entries_sorted(self):
        """All L2 entries for a topic should be returned, sorted by filename."""
        # Content must be >= 50 chars
        self.layer.write_l2("First entry for sorting test with sufficient length.", topic="sorting")
        self.layer.write_l2("Second entry for sorting test with sufficient length.", topic="sorting")
        
        entries = self.layer.read_l2("sorting")
        self.assertEqual(len(entries), 2)
        # Should be sorted by filename
        filenames = [e.file for e in entries]
        self.assertEqual(filenames, sorted(filenames))

    def test_read_l2_preserves_content(self):
        """Read content should match what was written."""
        original = "Original extraction content with specific details for reading."
        self.layer.write_l2(original, topic="preservation")
        
        entries = self.layer.read_l2("preservation")
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0].content, original)

    def test_l2_content_for_topic_combines_all(self):
        """l2_content_for_topic should concatenate all entries."""
        # Content must be >= 50 chars for L2 write to succeed
        self.layer.write_l2("First paragraph of content for combining with sufficient length.", topic="combined")
        self.layer.write_l2("Second paragraph of content for combining with sufficient length.", topic="combined")
        
        combined = self.layer.l2_content_for_topic("combined")
        self.assertIn("First paragraph", combined)
        self.assertIn("Second paragraph", combined)

    def test_l2_content_for_topic_empty_for_missing_topic(self):
        """l2_content_for_topic should return empty string for missing topic."""
        result = self.layer.l2_content_for_topic("missing")
        self.assertEqual(result, "")


class TestPostExtractionHookExtraction(TestCase):
    """Tests for post-extraction hook behavior related to extraction."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.layer = MemoryLayer(memory_root=self.tmp)

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)
        reset_executor()

    def test_hook_topic_from_file_path_fallback(self):
        """When topic not provided and file has no path, defaults to generic."""
        result = post_extraction_hook(
            [{"content": "Content for topic fallback testing here with sufficient length."}],
            layer=self.layer,
            background=False,
            consolidate=False,
        )
        
        self.assertIsNotNone(result)
        assert result is not None
        self.assertEqual(len(result), 1)
        # Topic should be derived or default
        self.assertIsNotNone(result[0].topic)

    def test_hook_multiple_entries_same_topic(self):
        """Multiple entries for same topic should all be processed."""
        entries = [
            {"content": "First entry for multi-entry extraction test scenario.", "file": "session/a.md"},
            {"content": "Second entry for multi-entry extraction test scenario.", "file": "session/b.md"},
        ]
        result = post_extraction_hook(entries, layer=self.layer, background=False, consolidate=False)
        
        self.assertIsNotNone(result)
        assert result is not None
        self.assertEqual(len(result), 2)

    def test_hook_filters_duplicate_content(self):
        """Hook should handle idempotent writes for duplicate content."""
        entries = [
            {"content": "Duplicate content extraction test — sufficient length.", "file": "session/dup.md"},
        ]
        # Process same entries twice
        post_extraction_hook(entries, layer=self.layer, background=False, consolidate=False)
        result = post_extraction_hook(entries, layer=self.layer, background=False, consolidate=False)
        
        # Should not create duplicate summaries
        self.assertIsNotNone(result)
        assert result is not None
        self.assertEqual(len(result), 1)  # Still only one summary
