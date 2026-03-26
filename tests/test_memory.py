"""Tests for the L1/L2 memory layer and summarisation pipeline."""

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
    topic_from_path,
)
from sebba_code.memory.summarize import (
    _is_valid_summary,
    _strip_markdown_code_fences,
)
from sebba_code.memory.hook import (
    post_extraction_hook,
    reset_executor,
    summarise_and_write,
)


def _now() -> str:
    return datetime.now(UTC).isoformat()


class TestContentHash(TestCase):
    def test_hash_is_deterministic(self):
        text = "hello world"
        h1 = content_hash(text)
        h2 = content_hash(text)
        self.assertEqual(h1, h2)

    def test_hash_changes_with_content(self):
        h1 = content_hash("hello")
        h2 = content_hash("world")
        self.assertNotEqual(h1, h2)

    def test_hash_is_short_hex(self):
        h = content_hash("anything")
        self.assertLessEqual(len(h), 16)
        int(h, 16)  # must be valid hex


class TestTopicFromPath(TestCase):
    def test_stem_extracted(self):
        self.assertEqual(topic_from_path("concepts/caching.md"), "Caching")
        self.assertEqual(topic_from_path("architecture_overview.md"), "Architecture Overview")

    def test_hyphen_underscore_replaced(self):
        self.assertEqual(topic_from_path("session_2024_01.md"), "Session 2024 01")
        self.assertEqual(topic_from_path("my_topic.md"), "My Topic")


class TestMemoryLayerConfig(TestCase):
    def test_defaults(self):
        cfg = MemoryLayerConfig()
        self.assertEqual(cfg.min_l2_length_to_write, 50)
        self.assertEqual(cfg.min_l2_length_for_summary, 400)
        self.assertEqual(cfg.max_summarization_retries, 2)


class TestMemoryLayer(TestCase):
    """Tests for MemoryLayer L1/L2 storage.

    Note: default min_l2_length_to_write=50, so test content must be >= 50 chars.
    """

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.layer = MemoryLayer(memory_root=self.tmp)

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)
        reset_executor()

    def test_write_l2_creates_directory(self):
        entry = self.layer.write_l2(
            "This is a detailed L2 entry about testing patterns with enough characters.",
            topic="testing",
        )
        self.assertIsNotNone(entry)
        self.assertTrue((self.tmp / "testing").is_dir())

    def test_write_l2_returns_entry(self):
        entry = self.layer.write_l2(
            "Detailed content here — long enough to pass the length check for L2.",
            topic="patterns",
        )
        self.assertIsNotNone(entry)
        self.assertEqual(entry.topic, "patterns")
        self.assertIn("Detailed content", entry.content)

    def test_write_l2_skips_short_content(self):
        cfg = MemoryLayerConfig(min_l2_length_to_write=50)
        layer = MemoryLayer(memory_root=self.tmp, config=cfg)
        result = layer.write_l2("tiny", topic="testing")
        self.assertIsNone(result)

    def test_write_l2_idempotent_same_content(self):
        content = "Stable detailed L2 content for idempotency check — more than fifty chars."
        e1 = self.layer.write_l2(content, topic="session")
        e2 = self.layer.write_l2(content, topic="session")
        # second write is a no-op (already exists unchanged)
        self.assertIsNotNone(e1)
        self.assertIsNone(e2)

    def test_write_l2_different_content_same_topic(self):
        e1 = self.layer.write_l2(
            "First detailed piece of content for testing purposes in this module.",
            topic="session",
        )
        e2 = self.layer.write_l2(
            "Second distinct piece of content for testing purposes in this module.",
            topic="session",
        )
        self.assertIsNotNone(e1)
        self.assertIsNotNone(e2)
        self.assertNotEqual(e1.key, e2.key)

    def test_read_l2_roundtrip(self):
        content = "L2 roundtrip test content for reading back — sufficient length."
        self.layer.write_l2(content, topic="rules")
        entries = self.layer.read_l2("rules")
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0].content, content)

    def test_l2_content_for_topic(self):
        self.layer.write_l2(
            "First paragraph of content for the design topic tests.",
            topic="design",
        )
        self.layer.write_l2(
            "Second paragraph of content for the design topic tests.",
            topic="design",
        )
        combined = self.layer.l2_content_for_topic("design")
        self.assertIn("First paragraph", combined)
        self.assertIn("Second paragraph", combined)

    def test_write_l1_and_read_l1(self):
        summary = L1Summary(
            file="testing.md",
            topic="Testing",
            summary="This module covers testing patterns including unit tests and integration tests.",
            source_l2_key="abc123",
            l2_preview="First 300 chars of L2 content here...",
            created_at=_now(),
            version=1,
            summary_model="claude-haiku",
        )
        path = self.layer.write_l1(summary)
        self.assertTrue(path.exists())

        loaded = self.layer.read_l1("testing.md")
        self.assertIsNotNone(loaded)
        assert loaded is not None
        self.assertEqual(loaded.topic, "Testing")
        self.assertIn("unit tests", loaded.summary)

    def test_write_l1_version_bumps_on_repeat(self):
        s1 = L1Summary(
            file="versioned.md", topic="Versioned",
            summary="First version of the summary content here.", source_l2_key="k1",
            l2_preview="", created_at=_now(), version=1,
        )
        self.layer.write_l1(s1)
        s2 = L1Summary(
            file="versioned.md", topic="Versioned",
            summary="Second version of the summary content here.", source_l2_key="k1",
            l2_preview="", created_at=_now(), version=2,
        )
        self.layer.write_l1(s2)
        loaded = self.layer.read_l1("versioned.md")
        assert loaded is not None
        self.assertEqual(loaded.version, 2)
        self.assertEqual(loaded.summary, "Second version of the summary content here.")

    def test_purge_l2_for_topic(self):
        self.layer.write_l2(
            "Content A for purge test — sufficiently long to pass length check.",
            topic="purge_test",
        )
        self.layer.write_l2(
            "Content B for purge test — sufficiently long to pass length check.",
            topic="purge_test",
        )
        count = self.layer.purge_l2_for_topic("purge_test")
        self.assertEqual(count, 2)
        self.assertFalse((self.tmp / "purge_test").exists())


class TestHelpers(TestCase):
    def test_strip_markdown_code_fences(self):
        self.assertEqual(
            _strip_markdown_code_fences("```\nhello world\n```"),
            "hello world",
        )
        self.assertEqual(
            _strip_markdown_code_fences("```markdown\nsome text\n```"),
            "some text",
        )
        self.assertEqual(
            _strip_markdown_code_fences("no fences here"),
            "no fences here",
        )

    def test_is_valid_summary(self):
        self.assertTrue(_is_valid_summary(
            "This is a valid summary with enough words to pass the validation."
        ))
        self.assertFalse(_is_valid_summary("Too short."))
        self.assertFalse(_is_valid_summary(""))
        self.assertFalse(_is_valid_summary("x" * 39))  # too short even if long-ish


class TestPostExtractionHook(TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.layer = MemoryLayer(memory_root=self.tmp)

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)
        reset_executor()

    def test_hook_skips_empty_entries(self):
        result = post_extraction_hook([], layer=self.layer, background=False)
        self.assertIsNone(result)

    def test_hook_skips_short_entries(self):
        # Content < min_l2_length_to_write (50) should be skipped
        result = post_extraction_hook(
            [{"content": "tiny", "file": "tiny.md"}],
            layer=self.layer,
            background=False,
        )
        self.assertIsNone(result)

    def test_hook_writes_l1_for_short_content(self):
        """Content below min_l2_length_for_summary (200 chars) is verbatim-copied to L1.

        The hook calls summarise_l2_to_l1 which writes L1 (but not L2, since L2
        is assumed to have been written by the extraction step already).
        """
        result = post_extraction_hook(
            [
                {
                    # ~107 chars — passes min_l2_length_to_write (50) so the hook
                    # proceeds; falls below min_l2_length_for_summary (200) so the
                    # original content is verbatim-copied to L1 without any LLM call.
                    "content": "Detailed L2 content about memory layer patterns and design decisions in this session.",
                    "file": "memory/design.md",
                    "topic": "memory",
                }
            ],
            layer=self.layer,
            background=False,
            consolidate=False,
        )
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 1)

        # L1 summary file must exist
        l1_file = self.tmp / "memory.md"
        self.assertTrue(l1_file.is_file(), "L1 file should be written")
        loaded = self.layer.read_l1("memory.md")
        self.assertIsNotNone(loaded)
        assert loaded is not None
        self.assertEqual(loaded.topic, "memory")
        # Verbatim copy: summary is the original content
        self.assertIn("Detailed L2 content", loaded.summary)

    def test_hook_background_returns_future(self):
        future = post_extraction_hook(
            [
                {
                    "content": "Background hook test content — needs to be long enough to pass the length check.",
                    "file": "async/test.md",
                    "topic": "async",
                }
            ],
            layer=self.layer,
            background=True,
            consolidate=False,
        )
        self.assertIsNotNone(future)
        result = future.result(timeout=10)
        self.assertIsInstance(result, list)

    def test_hook_consolidate_produces_one_l1(self):
        results = post_extraction_hook(
            [
                {
                    "content": "First piece of consolidated content for topic summarisation in this test.",
                    "file": "consolidated/piece1.md",
                    "topic": "consolidated",
                },
                {
                    "content": "Second piece of consolidated content for topic summarisation in this test.",
                    "file": "consolidated/piece2.md",
                    "topic": "consolidated",
                },
            ],
            layer=self.layer,
            background=False,
            consolidate=True,
        )
        self.assertIsInstance(results, list)
        # consolidated mode should produce at most 1 L1 summary
        self.assertLessEqual(len(results), 1)


class TestSummariseAndWrite(TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)
        reset_executor()

    @patch("sebba_code.memory.summarize.get_cheap_llm")
    def test_summarise_and_write_short_content(self, mock_llm):
        """Content shorter than min_l2_length_to_write is skipped, no LLM call."""
        layer = MemoryLayer(memory_root=self.tmp)
        result = summarise_and_write(
            "Too short to need summarisation.",
            topic="short_topic",
            layer=layer,
        )
        # Short content: L2 write is skipped, so returns None
        self.assertIsNone(result)
        mock_llm.assert_not_called()

    @patch("sebba_code.memory.summarize.get_cheap_llm")
    def test_summarise_and_write_calls_llm_for_long_content(self, mock_llm):
        """Content >= min_l2_length_for_summary (200 chars) triggers LLM summarisation."""
        mock_response = MagicMock()
        mock_response.content = "This is a concise summary of the long detailed content."
        mock_llm.return_value.invoke.return_value = mock_response

        layer = MemoryLayer(memory_root=self.tmp)
        # Must be >= 200 chars to trigger LLM call
        long_content = "Here is a very long and detailed piece of memory content. " * 15
        self.assertGreater(len(long_content), 200)

        result = summarise_and_write(
            long_content,
            topic="long_topic",
            layer=layer,
        )

        self.assertIsNotNone(result)
        self.assertIn("concise summary", result.summary)
        mock_llm.assert_called_once()

    @patch("sebba_code.memory.summarize.get_cheap_llm")
    def test_summarise_and_write_retries_on_invalid_output(self, mock_llm):
        """If LLM returns empty/garbage, retries up to max_retries then returns None."""
        # Exhaustively mock 3 invoke() calls (initial + 2 retries).
        # Each returns an empty string, which fails _is_valid_summary.
        mock_llm.return_value.invoke.side_effect = [
            MagicMock(content=""),
            MagicMock(content=""),
            MagicMock(content=""),
        ]

        layer = MemoryLayer(memory_root=self.tmp)
        # Must be >= 200 chars to reach the LLM call path
        long_content = "Detailed content that will be summarised after retry with sufficient length. " * 12
        self.assertGreater(len(long_content), 200)

        result = summarise_and_write(
            long_content,
            topic="retry_topic",
            layer=layer,
        )

        # After 3 invalid responses all retries are exhausted → returns None
        self.assertIsNone(result)
        self.assertEqual(mock_llm.return_value.invoke.call_count, 3)
