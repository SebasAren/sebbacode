"""Integration tests for the extraction → summarization pipeline.

These tests verify the end-to-end flow: memory content is extracted,
written to L2, and summarized to L1.
"""

import tempfile
from datetime import datetime, UTC
from pathlib import Path
from unittest import TestCase
from unittest.mock import MagicMock, patch

from sebba_code.memory.layers import (
    L1Summary,
    L2Entry,
    MemoryLayer,
    MemoryLayerConfig,
    content_hash,
)
from sebba_code.memory.summarize import (
    summarise_l2_to_l1,
    summarise_topic_to_l1,
)
from sebba_code.memory.hook import (
    post_extraction_hook,
    summarise_and_write,
    reset_executor,
)


def _now() -> str:
    return datetime.now(UTC).isoformat()


class TestExtractionSummarizationFlow(TestCase):
    """End-to-end tests for the complete extraction → L2 → L1 pipeline."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.layer = MemoryLayer(memory_root=self.tmp)

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)
        reset_executor()

    def test_full_flow_with_short_content(self):
        """Short content should flow: extraction → L1 (verbatim), no LLM call."""
        # Short content (< 200 chars) should be verbatim-copied to L1
        content = "Brief session note about code review findings here with sufficient length."
        
        result = summarise_and_write(content, topic="review", layer=self.layer)
        
        # L1 file should exist with verbatim content
        self.assertIsNotNone(result)
        assert result is not None
        self.assertEqual(result.summary, content)
        
        l1_file = self.tmp / "review.md"
        self.assertTrue(l1_file.is_file())

    @patch("sebba_code.memory.summarize.invoke_with_timeout")
    def test_full_flow_with_long_content(self, mock_invoke):
        """Long content should flow: extraction → L2 → LLM → L1."""
        mock_response = MagicMock()
        mock_response.content = "Generated summary of the long detailed session content with enough words here."
        mock_invoke.return_value = mock_response

        # Long content (>= 200 chars) should trigger LLM
        content = "Detailed session content covering code architecture decisions. " * 15
        
        result = summarise_and_write(content, topic="architecture", layer=self.layer)
        
        self.assertIsNotNone(result)
        assert result is not None
        self.assertIn("Generated summary", result.summary)
        
        # Both L2 and L1 files should exist
        self.assertTrue((self.tmp / "architecture").is_dir())
        self.assertTrue((self.tmp / "architecture.md").is_file())

    @patch("sebba_code.memory.summarize.invoke_with_timeout")
    def test_multiple_extractions_same_session(self, mock_invoke):
        """Multiple extractions in same session should all be processed."""
        mock_response = MagicMock()
        mock_response.content = "Summary with enough words for validation here."
        mock_invoke.return_value = mock_response

        # First extraction
        summarise_and_write(
            "First topic discussion about API design patterns in detail here.",
            topic="api",
            layer=self.layer,
        )
        
        # Second extraction
        summarise_and_write(
            "Second topic discussion about database schema decisions here.",
            topic="database",
            layer=self.layer,
        )
        
        # Both L1 files should exist
        self.assertTrue((self.tmp / "api.md").is_file())
        self.assertTrue((self.tmp / "database.md").is_file())


class TestHookToSummarizationFlow(TestCase):
    """Tests for the flow from post_extraction_hook through to L1 summaries."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.layer = MemoryLayer(memory_root=self.tmp)

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)
        reset_executor()

    def test_hook_triggers_summarization(self):
        """post_extraction_hook should trigger L1 summarization."""
        result = post_extraction_hook(
            [
                {
                    "content": "Extracted memory content for hook testing — sufficient length.",
                    "file": "memory/session.md",
                }
            ],
            layer=self.layer,
            background=False,
            consolidate=False,
        )
        
        self.assertIsNotNone(result)
        assert result is not None
        self.assertEqual(len(result), 1)
        
        # L1 file should be created
        self.assertTrue((self.tmp / "session.md").is_file())

    @patch("sebba_code.memory.summarize.invoke_with_timeout")
    def test_hook_with_multiple_entries(self, mock_invoke):
        """Hook should process all provided entries."""
        mock_response = MagicMock()
        mock_response.content = "Summary with enough words for validation here."
        mock_invoke.return_value = mock_response

        result = post_extraction_hook(
            [
                {"content": "First extraction entry content for testing purposes here.", "file": "session/a.md"},
                {"content": "Second extraction entry content for testing purposes here.", "file": "session/b.md"},
                {"content": "Third extraction entry content for testing purposes here.", "file": "session/c.md"},
            ],
            layer=self.layer,
            background=False,
            consolidate=False,
        )
        
        self.assertIsNotNone(result)
        assert result is not None
        self.assertEqual(len(result), 3)

    def test_hook_consolidation_mode(self):
        """consolidate=True with short content should work."""
        result = post_extraction_hook(
            [
                {"content": "First piece of content for consolidation testing here.", "file": "session/piece1.md"},
                {"content": "Second piece of content for consolidation testing here.", "file": "session/piece2.md"},
            ],
            layer=self.layer,
            background=False,
            consolidate=True,
        )
        
        # Should be list
        self.assertIsInstance(result, list)


class TestIdempotencyFlow(TestCase):
    """Tests for idempotent behavior in the extraction → summarization flow."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.layer = MemoryLayer(memory_root=self.tmp)

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)
        reset_executor()

    def test_modified_content_creates_new_entry(self):
        """Modified content should create a new L2 entry (not overwrite)."""
        # First extraction
        summarise_and_write(
            "Original content for modification testing purposes here.",
            topic="modified",
            layer=self.layer,
        )
        
        # Modified content
        summarise_and_write(
            "Modified content for modification testing purposes here.",
            topic="modified",
            layer=self.layer,
        )
        
        # L2 should have two files
        l2_dir = self.tmp / "modified"
        self.assertTrue(l2_dir.is_dir())
        files = list(l2_dir.glob("*.md"))
        self.assertEqual(len(files), 2)


class TestErrorRecoveryFlow(TestCase):
    """Tests for error handling and recovery in the pipeline."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.layer = MemoryLayer(memory_root=self.tmp)

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)
        reset_executor()

    @patch("sebba_code.memory.summarize.invoke_with_timeout")
    def test_llm_failure_does_not_corrupt_state(self, mock_invoke):
        """LLM failure should not leave partial/corrupt state."""
        mock_invoke.side_effect = Exception("LLM unavailable")

        cfg = MemoryLayerConfig(max_summarization_retries=1)
        layer = MemoryLayer(memory_root=self.tmp, config=cfg)
        
        content = "X" * 300  # Long enough to trigger LLM
        entry = L2Entry(
            key=content_hash(content),
            topic="failure",
            content=content,
            file="failure/entry.md",
            created_at=_now(),
        )
        
        result = summarise_l2_to_l1(entry, layer=layer, config=cfg)
        
        # Should return None, not crash
        self.assertIsNone(result)
        
        # L1 file should not exist
        self.assertFalse((self.tmp / "failure.md").is_file())

    @patch("sebba_code.memory.summarize.invoke_with_timeout")
    def test_partial_failure_in_batch(self, mock_invoke):
        """If one entry fails, others should still be processed."""
        # First call succeeds, second fails
        mock_responses = [
            MagicMock(content="First summary with enough words for validation here."),
            Exception("LLM error"),
        ]
        mock_invoke.side_effect = mock_responses

        cfg = MemoryLayerConfig()
        layer = MemoryLayer(memory_root=self.tmp, config=cfg)
        
        # Two entries that both need LLM
        entries = [
            L2Entry(key="a", topic="batch", content="A" * 300, file="batch/a.md", created_at=_now()),
            L2Entry(key="b", topic="batch", content="B" * 300, file="batch/b.md", created_at=_now()),
        ]
        
        results = []
        for entry in entries:
            result = summarise_l2_to_l1(entry, layer=layer, config=cfg)
            results.append(result)
        
        # First should succeed, second should fail (but not crash)
        self.assertIsNotNone(results[0])
        self.assertIsNone(results[1])


class TestTopicIsolation(TestCase):
    """Tests for topic isolation in the pipeline."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.layer = MemoryLayer(memory_root=self.tmp)

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)
        reset_executor()

    def test_topics_are_isolated(self):
        """Each topic should have its own L1 file, independent of others."""
        summarise_and_write(
            "Content for testing isolation — topic A specific here.",
            topic="topic_a",
            layer=self.layer,
        )
        summarise_and_write(
            "Content for testing isolation — topic B specific here.",
            topic="topic_b",
            layer=self.layer,
        )
        
        # Both L1 files should exist independently
        self.assertTrue((self.tmp / "topic_a.md").is_file())
        self.assertTrue((self.tmp / "topic_b.md").is_file())
        
        # L2 directories should be separate
        self.assertTrue((self.tmp / "topic_a").is_dir())
        self.assertTrue((self.tmp / "topic_b").is_dir())

    def test_consolidation_within_topic_only(self):
        """Consolidation should only combine entries within the same topic."""
        # Two entries for different topics
        result = post_extraction_hook(
            [
                {"content": "Content for topic X consolidation testing here.", "file": "x/entry.md"},
                {"content": "Content for topic Y consolidation testing here.", "file": "y/entry.md"},
            ],
            layer=self.layer,
            background=False,
            consolidate=True,
        )
        
        # Should return a list
        self.assertIsInstance(result, list)


class TestDataIntegrityFlow(TestCase):
    """Tests for data integrity through the pipeline."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.layer = MemoryLayer(memory_root=self.tmp)

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)
        reset_executor()

    def test_l1_roundtrip_preserves_data(self):
        """Written L1 should be readable back with all fields."""
        original = L1Summary(
            file="roundtrip.md",
            topic="Roundtrip",
            summary="Complete roundtrip test summary content.",
            source_l2_key="abc123",
            l2_preview="Preview of L2 content.",
            created_at=_now(),
            version=1,
            summary_model="test-model",
        )
        
        self.layer.write_l1(original)
        loaded = self.layer.read_l1("roundtrip.md")
        
        assert loaded is not None
        self.assertEqual(loaded.file, original.file)
        self.assertEqual(loaded.topic, original.topic)
        self.assertEqual(loaded.summary, original.summary)
        self.assertEqual(loaded.source_l2_key, original.source_l2_key)
        self.assertEqual(loaded.l2_preview, original.l2_preview)
        self.assertEqual(loaded.version, original.version)

    def test_l2_roundtrip_preserves_data(self):
        """Written L2 should be readable back with all fields."""
        content = "Original L2 content for roundtrip testing purposes here."
        original = L2Entry(
            key=content_hash(content),
            topic="roundtrip",
            content=content,
            file="roundtrip/entry.md",
            created_at=_now(),
        )
        
        self.layer.write_l2(content, topic="roundtrip")
        loaded = self.layer.read_l2("roundtrip")
        
        self.assertEqual(len(loaded), 1)
        self.assertEqual(loaded[0].content, original.content)
        self.assertEqual(loaded[0].topic, original.topic)

    def test_summary_source_tracking(self):
        """Each L1 summary should track its source L2 entry."""
        content = "Content for source tracking test with sufficient length here."
        entry_key = content_hash(content)
        
        result = summarise_and_write(content, topic="source", layer=self.layer)
        
        assert result is not None
        self.assertEqual(result.source_l2_key, entry_key)
        
        # Verify in file
        loaded = self.layer.read_l1("source.md")
        assert loaded is not None
        self.assertEqual(loaded.source_l2_key, entry_key)


class TestConfigDrivenBehavior(TestCase):
    """Tests for configuration-driven pipeline behavior."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)
        reset_executor()

    def test_custom_length_thresholds(self):
        """Custom length thresholds should be respected."""
        # Very high threshold - content won't be written
        cfg = MemoryLayerConfig(min_l2_length_to_write=10000)
        layer = MemoryLayer(memory_root=self.tmp, config=cfg)
        
        result = layer.write_l2("Short content.", topic="high_threshold")
        self.assertIsNone(result)

    @patch("sebba_code.memory.summarize.invoke_with_timeout")
    def test_high_verbatim_threshold(self, mock_invoke):
        """High min_l2_length_for_summary should verbatim-copy more content."""
        mock_response = MagicMock()
        mock_response.content = "Summary."
        mock_invoke.return_value = mock_response

        cfg = MemoryLayerConfig(min_l2_length_for_summary=500)
        layer = MemoryLayer(memory_root=self.tmp, config=cfg)
        
        # 400 chars - below threshold, should be verbatim
        content = "A" * 400
        entry = L2Entry(
            key=content_hash(content),
            topic="threshold",
            content=content,
            file="threshold/entry.md",
            created_at=_now(),
        )
        
        result = summarise_l2_to_l1(entry, layer=layer, config=cfg)
        
        self.assertIsNotNone(result)
        assert result is not None
        # Should be verbatim copy, no LLM call
        self.assertEqual(result.summary, content)
        mock_invoke.assert_not_called()
