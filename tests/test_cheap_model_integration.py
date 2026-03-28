"""Integration tests for all cheap model tasks.

These tests hit the real LLM endpoint — run with:
    uv run pytest -m integration -v
    mise run test-integration
"""

import pytest

from sebba_code.llm import get_cheap_llm, invoke_with_timeout, reset_llm_clients
from sebba_code.nodes.worker import (
    CommitClassification,
    ExtractionResult,
    TaskSummaryResult,
)


@pytest.fixture(autouse=True)
def _reset_llm():
    """Reset cached LLM clients after each test."""
    yield
    reset_llm_clients()


# ---------------------------------------------------------------------------
# 0. Smoke test — basic connectivity and latency
# ---------------------------------------------------------------------------

@pytest.mark.integration
class TestCheapModelSmoke:

    def test_simple_response(self):
        """Baseline: cheap model can respond to a trivial prompt."""
        llm = get_cheap_llm()
        result = invoke_with_timeout(llm, "Reply with the word 'hello'.", timeout_seconds=15)

        assert result is not None
        assert len(result.content) > 0


# ---------------------------------------------------------------------------
# 1. Task Summarization
# ---------------------------------------------------------------------------

@pytest.mark.integration
class TestTaskSummarization:

    def test_returns_valid_structured_output(self):
        prompt = (
            "Summarize this coding session for a progress log.\n\n"
            "Task: Add input validation to the user registration endpoint\n\n"
            "Conversation:\n"
            "Human: Add email and password validation to POST /api/register\n"
            "AI: I'll add validation using pydantic. Reading the current handler...\n"
            "AI: Added EmailStr validator and minimum password length check.\n"
            "AI: Updated the tests to cover invalid inputs.\n\n"
            "Respond with JSON:\n"
            '{"summary": "one-line summary",'
            ' "what_i_did": "bullet list of actions",'
            ' "decisions_made": "choices and rationale (or empty string)",'
            ' "files_touched": "comma-separated files modified (or empty string)"}'
        )
        llm = get_cheap_llm().with_structured_output(TaskSummaryResult)
        result = invoke_with_timeout(llm, prompt, timeout_seconds=45)

        assert result is not None
        assert isinstance(result, TaskSummaryResult)
        assert result.summary
        assert result.what_i_did


# ---------------------------------------------------------------------------
# 2. Commit Message Generation
# ---------------------------------------------------------------------------

VALID_COMMIT_TYPES = {"feat", "fix", "docs", "refactor", "test", "chore"}


@pytest.mark.integration
class TestCommitMessageGeneration:

    def test_returns_valid_commit_classification(self):
        prompt = (
            "Generate a conventional commit classification for this change.\n\n"
            "Task: Add input validation to user registration\n"
            "Summary: Added email and password validation to the registration endpoint\n"
            "Files: src/api/routes/register.py, tests/test_register.py\n\n"
            'Respond with JSON: {"type": "feat|fix|docs|refactor|test|chore", '
            '"scope": "optional short scope", "description": "imperative mood, under 72 chars"}'
        )
        llm = get_cheap_llm().with_structured_output(CommitClassification)
        result = invoke_with_timeout(llm, prompt, timeout_seconds=30)

        assert result is not None
        assert isinstance(result, CommitClassification)
        assert result.type in VALID_COMMIT_TYPES
        assert result.description
        assert len(result.description) <= 72


# ---------------------------------------------------------------------------
# 3. Per-Task Memory Extraction
# ---------------------------------------------------------------------------

@pytest.mark.integration
class TestMemoryExtraction:

    def test_returns_valid_extraction_structure(self):
        prompt = """Read this task result and extract lasting knowledge.

## Task: Migrate authentication from JWT to session-based auth

### What was done
- Replaced JWT middleware with session middleware in src/api/middleware/auth.py
- Added Redis session store configuration in src/config/session.py
- Updated all route handlers to use request.session instead of decoded JWT
- Added session cleanup cron job

### Decisions Made
- Chose Redis over Memcached for session storage because we already run Redis for caching
- Set session TTL to 24 hours based on security team recommendation
- Kept JWT support for API-only clients behind a feature flag

### Files Touched
src/api/middleware/auth.py, src/config/session.py, src/api/routes/*.py

## Current Memory Index
- **architecture**: Monorepo with api and frontend apps
- **conventions**: TypeScript strict mode, vitest for testing

## Existing Memory Files
L1: architecture.md — Monorepo overview
L2: architecture/api-routes.md — API route structure

## Existing Rules
rules/testing.md — paths: **/*.test.ts — Use vitest

Extract JSON:
{
  "memory_updates": [
    {"file": "architecture/example.md", "action": "create|append|replace_section", "section": "optional", "content": "..."}
  ],
  "index_updates": [
    {"old_line": "existing line or null", "new_line": "updated summary"}
  ],
  "new_rules": [
    {"file": "rules/example.md", "paths": ["glob/**"] , "content": "rule text"}
  ]
}

Rules:
- PREFER updating existing files over creating new ones
- Only extract genuinely NEW knowledge not already in memory
- Empty lists if nothing new was learned
- Keep index lines under 100 characters
- The "content" field must be DETAILED and COMPREHENSIVE
"""
        llm = get_cheap_llm().with_structured_output(ExtractionResult)
        result = invoke_with_timeout(llm, prompt, timeout_seconds=60)

        assert result is not None
        assert isinstance(result, ExtractionResult)
        assert isinstance(result.memory_updates, list)
        assert isinstance(result.index_updates, list)
        assert isinstance(result.new_rules, list)

        for mu in result.memory_updates:
            assert mu.file
            assert mu.action in {"create", "append", "replace_section"}
            assert mu.content

        for iu in result.index_updates:
            assert iu.new_line

        for nr in result.new_rules:
            assert nr.file
            assert isinstance(nr.paths, list)
            assert nr.content


# ---------------------------------------------------------------------------
# 4. Codebase Exploration
# ---------------------------------------------------------------------------

@pytest.mark.integration
class TestCodebaseExploration:

    def test_llm_can_bind_and_call_tools(self, tmp_path, monkeypatch):
        """Test that the cheap LLM can bind tools and produce tool calls."""
        from langchain_core.messages import HumanMessage, SystemMessage

        from sebba_code.tools.explore_agent import _EXPLORE_SYSTEM, _INNER_TOOLS

        monkeypatch.chdir(tmp_path)

        # Create a file to explore
        (tmp_path / "calculator.py").write_text(
            "def add(a: int, b: int) -> int:\n"
            "    return a + b\n\n"
            "def multiply(a: int, b: int) -> int:\n"
            "    return a * b\n"
        )

        llm = get_cheap_llm().bind_tools(_INNER_TOOLS)
        messages = [
            SystemMessage(content=_EXPLORE_SYSTEM),
            HumanMessage(content="What functions are defined in calculator.py?"),
        ]

        response = invoke_with_timeout(llm, messages, timeout_seconds=30)

        assert response is not None
        # The LLM should either answer directly or make tool calls
        has_content = bool(response.content)
        has_tool_calls = bool(getattr(response, "tool_calls", None))
        assert has_content or has_tool_calls


# ---------------------------------------------------------------------------
# 5. L2→L1 Summarization
# ---------------------------------------------------------------------------
# Already covered by existing integration tests in:
#   tests/test_memory/test_summarization.py
#     - TestSummarizeL2ToL1.test_summary_written_to_l1_file
#     - TestSummariseAndWriteIntegration.test_full_pipeline_long_content
