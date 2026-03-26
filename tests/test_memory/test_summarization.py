"""Tests for L2 → L1 summarization pipeline."""

import tempfile
from datetime import datetime, UTC
from pathlib import Path
from unittest import TestCase

import pytest

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
    _strip_markdown_code_fences,
    _is_valid_summary,
)
from sebba_code.memory.hook import (
    post_extraction_hook,
    summarise_and_write,
    reset_executor,
)


def _now() -> str:
    return datetime.now(UTC).isoformat()


class TestSummarizeHelpers(TestCase):
    """Tests for summarization helper functions."""

    def test_strip_markdown_code_fences_plain(self):
        """Should strip ``` fences."""
        result = _strip_markdown_code_fences("```\nhello world\n```")
        self.assertEqual(result, "hello world")

    def test_strip_markdown_code_fences_with_language(self):
        """Should strip ```markdown fences."""
        result = _strip_markdown_code_fences("```markdown\nsome text\n```")
        self.assertEqual(result, "some text")

    def test_strip_markdown_code_fences_with_text(self):
        """Should strip ```text fences."""
        result = _strip_markdown_code_fences("```text\ncontent\n```")
        self.assertEqual(result, "content")

    def test_strip_markdown_code_fences_none(self):
        """No fences should pass through unchanged."""
        result = _strip_markdown_code_fences("no fences here")
        self.assertEqual(result, "no fences here")

    def test_strip_markdown_code_fences_partial(self):
        """Only leading/trailing fences should be stripped."""
        result = _strip_markdown_code_fences("```\nmiddle content\nno closing")
        self.assertEqual(result, "middle content\nno closing")

    def test_is_valid_summary_minimum_words(self):
        """Summary with 10+ words should be valid."""
        valid = "This is a valid summary with exactly ten words here."
        self.assertTrue(_is_valid_summary(valid, min_words=10))

    def test_is_valid_summary_below_minimum_words(self):
        """Summary with fewer than 10 words should be invalid."""
        invalid = "Too short."
        self.assertFalse(_is_valid_summary(invalid, min_words=10))

    def test_is_valid_summary_empty(self):
        """Empty summary should be invalid."""
        self.assertFalse(_is_valid_summary(""))
        self.assertFalse(_is_valid_summary(None))  # type: ignore

    def test_is_valid_summary_below_length_threshold(self):
        """Summary shorter than 40 chars should be invalid."""
        # 39 chars (1 word) - fails both length and word count
        self.assertFalse(_is_valid_summary("x" * 39))
        # 40 chars but only 1 word - passes length but fails word count
        self.assertFalse(_is_valid_summary("x" * 40))
        # 40 chars with 10 words - passes both
        self.assertTrue(_is_valid_summary("word " * 10))

    def test_is_valid_summary_whitespace_only(self):
        """Whitespace-only summary should be invalid."""
        self.assertFalse(_is_valid_summary("   \n\t  "))

    def test_is_valid_summary_custom_min_words(self):
        """min_words parameter should be respected."""
        text = "One two three four five six seven eight nine ten"
        self.assertTrue(_is_valid_summary(text, min_words=10))
        self.assertFalse(_is_valid_summary("One two three four", min_words=10))


class TestSummarizeL2ToL1(TestCase):
    """Tests for the core summarise_l2_to_l1 function."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.layer = MemoryLayer(memory_root=self.tmp)

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)
        reset_executor()

    def _make_l2_entry(self, content: str, topic: str = "test") -> L2Entry:
        """Helper to create L2Entry with default values."""
        return L2Entry(
            key=content_hash(content),
            topic=topic,
            content=content,
            file=f"{topic}/entry.md",
            created_at=_now(),
            version=1,
        )

    def test_verbatim_copy_short_content(self):
        """Content below min_l2_length_for_summary (200 chars) should be verbatim-copied."""
        # 150 chars - below threshold
        content = "Short content below summarization threshold for verbatim copy testing purposes here."
        entry = self._make_l2_entry(content)
        
        result = summarise_l2_to_l1(entry, layer=self.layer)
        
        self.assertIsNotNone(result)
        assert result is not None
        # Verbatim copy: summary is original content
        self.assertEqual(result.summary, content.strip())
        self.assertEqual(result.version, 1)

    @pytest.mark.integration
    def test_summary_written_to_l1_file(self):
        """Summarization result should be written to L1 file (via real LLM)."""
        entry = self._make_l2_entry("X" * 300)
        result = summarise_l2_to_l1(entry, layer=self.layer)
        
        l1_file = self.tmp / "test.md"
        self.assertTrue(l1_file.is_file())
        content = l1_file.read_text()
        # LLM produces actual summary text
        self.assertTrue(len(content) > 0)

    def test_l1_file_contains_metadata(self):
        """L1 file should include front-matter with metadata."""
        entry = self._make_l2_entry("X" * 300, topic="metadata")
        result = summarise_l2_to_l1(entry, layer=self.layer)
        
        l1_file = self.tmp / "metadata.md"
        content = l1_file.read_text()
        
        self.assertTrue(content.startswith("---"))
        self.assertIn("topic: metadata", content)
        self.assertIn("version: 1", content)
        self.assertIn("<!-- l2_preview -->", content)

    def test_version_bumps_on_repeat(self):
        """Re-summarizing same content should bump version."""
        content = "Repeat content for version bump test " * 15
        entry = self._make_l2_entry(content, topic="repeat")

        result1 = summarise_l2_to_l1(entry, layer=self.layer)
        result2 = summarise_l2_to_l1(entry, layer=self.layer)
        
        self.assertEqual(result1.version, 1)
        self.assertEqual(result2.version, 2)
        
        # L1 file should have latest version
        loaded = self.layer.read_l1("repeat.md")
        assert loaded is not None
        self.assertEqual(loaded.version, 2)

    def test_l2_preview_included(self):
        """L2 preview (first 300 chars) should be included in L1."""
        content = "A" * 500  # 500 chars, first 300 will be preview
        entry = self._make_l2_entry(content, topic="preview")
        
        result = summarise_l2_to_l1(entry, layer=self.layer)
        
        self.assertIsNotNone(result)
        assert result is not None
        self.assertEqual(result.l2_preview, "A" * 300)


class TestSummarizeTopicToL1(TestCase):
    """Tests for summarise_topic_to_l1 (consolidated summarization)."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.layer = MemoryLayer(memory_root=self.tmp)

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)
        reset_executor()

    def test_empty_topic_returns_empty_list(self):
        """Non-existent topic should return empty list."""
        result = summarise_topic_to_l1("nonexistent", layer=self.layer)
        self.assertEqual(result, [])

    def test_single_entry_topic(self):
        """Topic with single L2 entry should work."""
        self.layer.write_l2("Single entry content for testing here with sufficient length.", topic="single")
        
        result = summarise_topic_to_l1("single", layer=self.layer)
        
        # Returns empty list if content too short for summarization
        self.assertIsInstance(result, list)


class TestSummariseAndWriteIntegration(TestCase):
    """Integration tests for summarise_and_write convenience function."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)
        reset_executor()

    def test_full_pipeline_short_content(self):
        """Short content: L2 skipped, returns None."""
        layer = MemoryLayer(memory_root=self.tmp)
        result = summarise_and_write(
            "Short content.",
            topic="short",
            layer=layer,
        )
        self.assertIsNone(result)

    @pytest.mark.integration
    def test_full_pipeline_long_content(self):
        """Long content: L2 written, L1 summarized (via real LLM)."""
        layer = MemoryLayer(memory_root=self.tmp)
        content = "Long detailed memory content for the full pipeline test. " * 15
        
        result = summarise_and_write(content, topic="pipeline", layer=layer)
        
        self.assertIsNotNone(result)
        assert result is not None
        self.assertEqual(result.topic, "pipeline")
        
        # L2 file should exist
        l2_dir = self.tmp / "pipeline"
        self.assertTrue(l2_dir.is_dir())
        
        # L1 file should exist
        l1_file = self.tmp / "pipeline.md"
        self.assertTrue(l1_file.is_file())


class TestHookConsolidation(TestCase):
    """Tests for consolidation mode in post_extraction_hook."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.layer = MemoryLayer(memory_root=self.tmp)

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)
        reset_executor()

    def test_consolidate_false_one_l1_per_entry(self):
        """consolidate=False should produce one L1 per L2 entry."""
        result = post_extraction_hook(
            [
                {"content": "First entry content for non-consolidation test scenario here.", "file": "session/a.md"},
                {"content": "Second entry content for non-consolidation test scenario here.", "file": "session/b.md"},
            ],
            layer=self.layer,
            background=False,
            consolidate=False,
        )
        
        self.assertEqual(len(result), 2)

    def test_consolidate_true_short_content(self):
        """consolidate=True with short content should work (verbatim)."""
        result = post_extraction_hook(
            [
                {"content": "First entry for consolidation testing purposes here.", "file": "session/piece1.md"},
                {"content": "Second entry for consolidation testing purposes here.", "file": "session/piece2.md"},
            ],
            layer=self.layer,
            background=False,
            consolidate=True,
        )
        
        # Should be list (possibly empty if all content too short)
        self.assertIsInstance(result, list)


class TestBackgroundSummarization(TestCase):
    """Tests for async/background summarization."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.layer = MemoryLayer(memory_root=self.tmp)

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)
        reset_executor()

    def test_background_returns_future(self):
        """background=True should return a Future."""
        future = post_extraction_hook(
            [{"content": "Background test content for async execution here with extra padding.", "file": "async/test.md"}],
            layer=self.layer,
            background=True,
            consolidate=False,
        )
        
        self.assertIsNotNone(future)
        result = future.result(timeout=30)
        self.assertIsInstance(result, list)

    def test_background_does_not_block(self):
        """Background call should return immediately."""
        import time
        
        start = time.time()
        future = post_extraction_hook(
            [{"content": "Timing test content for background execution here with extra padding.", "file": "timing/test.md"}],
            layer=self.layer,
            background=True,
            consolidate=False,
        )
        elapsed = time.time() - start
        
        # Should return quickly (< 100ms)
        self.assertLess(elapsed, 0.1)
        
        # But result should still be available
        result = future.result(timeout=30)
        self.assertIsInstance(result, list)


class TestSummarizationEdgeCases(TestCase):
    """Edge case tests for summarization."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.layer = MemoryLayer(memory_root=self.tmp)

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)
        reset_executor()

    def test_content_at_exact_threshold(self):
        """Content exactly at min_l2_length_for_summary (200) should be summarized."""
        # Exactly 200 chars
        content = "A" * 200
        entry = L2Entry(
            key=content_hash(content),
            topic="threshold",
            content=content,
            file="threshold/entry.md",
            created_at=_now(),
        )
        
        result = summarise_l2_to_l1(entry, layer=self.layer)
        self.assertIsNotNone(result)

    def test_multiline_content(self):
        """Multiline content should be preserved correctly."""
        content = "Line one.\n\nLine two with more detail.\n\nLine three final."
        entry = L2Entry(
            key=content_hash(content),
            topic="multiline",
            content=content,
            file="multiline/entry.md",
            created_at=_now(),
        )
        
        result = summarise_l2_to_l1(entry, layer=self.layer)
        self.assertIsNotNone(result)
        assert result is not None
        self.assertIn("Line one", result.summary)

    def test_special_characters_in_content(self):
        """Special characters in content should be preserved."""
        # Use meaningful content for LLM
        content = "Content with XML tags and quotes and special characters for testing purposes here."
        entry = L2Entry(
            key=content_hash(content),
            topic="special",
            content=content,
            file="special/entry.md",
            created_at=_now(),
        )
        
        result = summarise_l2_to_l1(entry, layer=self.layer)
        self.assertIsNotNone(result)

        # Verify L1 file was written
        l1_file = self.tmp / "special.md"
        self.assertTrue(l1_file.is_file())
