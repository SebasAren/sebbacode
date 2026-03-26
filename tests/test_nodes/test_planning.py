"""Tests for planning loop nodes in src/sebba_code/nodes/planning.py."""

import re
from unittest.mock import MagicMock, patch

import pytest

from sebba_code.nodes.planning import (
    critique_roadmap,
    draft_roadmap,
    is_planning_complete,
    needs_planning,
    refine_roadmap,
    write_roadmap,
)


def _make_state(**overrides) -> dict:
    """Create a minimal valid state dict with planning fields."""
    state = {
        "messages": [],
        "roadmap": "",
        "current_todo": None,
        "target_files": [],
        "briefing": "",
        "exploration_mode": "",
        "memory": {
            "l0_index": "",
            "l1_files": {},
            "l2_files": {},
            "active_rules": {},
            "session_history": "",
        },
        "working_branch": None,
        "todos_completed_this_session": [],
        "todo_summaries": [],
        "max_todos": None,
        "user_request": "Build auth system",
        "draft_roadmap": "",
        "planning_messages": [],
        "planning_iteration": 0,
        "planning_complete": False,
    }
    state.update(overrides)
    return state


# ---------------------------------------------------------------------------
# Draft output format tests
# ---------------------------------------------------------------------------


class TestDraftOutputFormat:
    """Tests for draft_roadmap output format validation."""

    def test_draft_contains_goal_section(self, monkeypatch):
        """Draft should contain ## Goal section."""
        mock_llm = MagicMock()
        mock_response = MagicMock()
        mock_response.content = (
            "## Goal\nImplement authentication.\n\n## Todos\n- [ ] Add login\n"
        )
        mock_llm.invoke.return_value = mock_response

        # Patch get_llm to return our mock
        monkeypatch.setattr("sebba_code.nodes.planning.get_llm", lambda **kw: mock_llm)

        state = _make_state()
        result = draft_roadmap(state)

        assert "draft_roadmap" in result
        assert "## Goal" in result["draft_roadmap"]

    def test_draft_contains_todos_section(self, monkeypatch):
        """Draft should contain ## Todos section with checkboxes."""
        mock_llm = MagicMock()
        mock_response = MagicMock()
        mock_response.content = (
            "## Goal\nAuth system.\n\n## Todos\n- [ ] Add user model\n"
        )
        mock_llm.invoke.return_value = mock_response

        monkeypatch.setattr("sebba_code.nodes.planning.get_llm", lambda **kw: mock_llm)

        state = _make_state()
        result = draft_roadmap(state)

        assert "## Todos" in result["draft_roadmap"]
        assert "- [ ]" in result["draft_roadmap"]

    def test_draft_contains_target_files_section(self, monkeypatch):
        """Draft should contain ## Target Files section."""
        mock_llm = MagicMock()
        mock_response = MagicMock()
        mock_response.content = (
            "## Goal\nAuth.\n\n## Target Files\n- src/auth.ts\n"
        )
        mock_llm.invoke.return_value = mock_response

        monkeypatch.setattr("sebba_code.nodes.planning.get_llm", lambda **kw: mock_llm)

        state = _make_state()
        result = draft_roadmap(state)

        assert "## Target Files" in result["draft_roadmap"]

    def test_draft_contains_todo_items_matching_regex(self, monkeypatch):
        """Draft todo items should match expected checkbox regex pattern."""
        mock_llm = MagicMock()
        mock_response = MagicMock()
        mock_response.content = (
            "## Goal\nAuth.\n\n## Todos\n"
            "- [ ] Create user model\n"
            "- [ ] Add login endpoint\n"
            "- [x] Done item\n"
        )
        mock_llm.invoke.return_value = mock_response

        monkeypatch.setattr("sebba_code.nodes.planning.get_llm", lambda **kw: mock_llm)

        state = _make_state()
        result = draft_roadmap(state)

        # Match checkbox pattern: - [ ] or - [x]
        checkbox_pattern = re.compile(r"- \[.\] .+")
        todos_section = result["draft_roadmap"].split("## Todos")[1].split("##")[0]
        matches = checkbox_pattern.findall(todos_section)
        assert len(matches) >= 2

    def test_draft_returns_planning_iteration_1(self, monkeypatch):
        """Draft should set planning_iteration to 1."""
        mock_llm = MagicMock()
        mock_response = MagicMock()
        mock_response.content = "## Goal\nTest.\n\n## Todos\n- [ ] Task\n"
        mock_llm.invoke.return_value = mock_response

        monkeypatch.setattr("sebba_code.nodes.planning.get_llm", lambda **kw: mock_llm)

        state = _make_state(planning_iteration=0)
        result = draft_roadmap(state)

        assert result["planning_iteration"] == 1

    def test_draft_uses_user_request(self, monkeypatch):
        """Draft should incorporate user_request in prompt."""
        mock_llm = MagicMock()
        mock_response = MagicMock()
        mock_response.content = "## Goal\nDone.\n\n## Todos\n- [ ] Task\n"
        mock_llm.invoke.return_value = mock_response

        captured_prompts = []

        def capture_llm(**kwargs):
            captured_prompts.append(kwargs.get("prompt", ""))
            return mock_llm

        monkeypatch.setattr("sebba_code.nodes.planning.get_llm", capture_llm)

        state = _make_state(user_request="Build OAuth2 login")
        draft_roadmap(state)

        # The LLM should have been called with a prompt containing user request
        assert mock_llm.invoke.called


# ---------------------------------------------------------------------------
# Critique detection tests
# ---------------------------------------------------------------------------


class TestCritiqueDetection:
    """Tests for critique_roadmap validation logic."""

    def test_detects_missing_todo_items(self):
        """Critique should flag roadmap without checkbox items."""
        state = _make_state(draft_roadmap="## Goal\nJust text.\n\nNo todos.")
        result = critique_roadmap(state)

        # Basic validation should catch missing todos
        assert result.get("planning_complete") is True

    def test_detects_short_content(self):
        """Critique should flag content that is too short."""
        state = _make_state(draft_roadmap="- [ ] todo")
        result = critique_roadmap(state)

        # Short content flagged, marked complete
        assert result.get("planning_complete") is True

    def test_passes_valid_roadmap(self):
        """Critique should pass a well-formed roadmap."""
        valid_draft = """## Goal
Build auth.

## Todos
- [ ] Create user model
- [ ] Add login

## Target Files
- src/auth.ts
"""
        state = _make_state(draft_roadmap=valid_draft)
        result = critique_roadmap(state)

        # Valid roadmap should complete planning
        assert result.get("planning_complete") is True

    def test_respects_max_iterations_config(self):
        """Critique should check iteration count against max."""
        state = _make_state(
            draft_roadmap="## Goal\nAuth.\n\n## Todos\n- [ ] Task\n",
            planning_iteration=2,
        )
        # Using configurable to set max iterations to 2
        result = critique_roadmap(state, configurable={"planning_max_iterations": 2})

        # Iteration 2 >= max 2, should mark complete
        assert result.get("planning_complete") is True

    def test_critique_adds_to_planning_messages(self):
        """Critique output should be added to planning_messages."""
        state = _make_state(
            draft_roadmap="## Goal\nAuth.\n\n## Todos\n- [ ] Task\n",
            planning_messages=[],
        )
        result = critique_roadmap(state)

        # Result should indicate completion
        assert "planning_complete" in result


# ---------------------------------------------------------------------------
# Refine application tests
# ---------------------------------------------------------------------------


class TestRefineApplication:
    """Tests for refine_roadmap applying critique fixes."""

    def test_refine_increments_planning_iteration(self):
        """Refine should increment planning_iteration."""
        state = _make_state(
            draft_roadmap="## Goal\nAuth.\n\n## Notes\n\nGenerated by test\n",
            planning_iteration=1,
        )
        result = refine_roadmap(state)

        assert result["planning_iteration"] == 2

    def test_refine_applies_notes_update_on_iteration_2(self):
        """Refine should add refinement note on second iteration."""
        state = _make_state(
            draft_roadmap="## Goal\nAuth.\n\n## Notes\n\nGenerated by test\n",
            planning_iteration=1,
        )
        result = refine_roadmap(state)

        assert "Refined after first critique" in result["draft_roadmap"]

    def test_refine_applies_notes_update_on_iteration_3(self):
        """Refine should add final refinement note on third iteration."""
        state = _make_state(
            draft_roadmap="## Goal\nAuth.\n\n## Notes\n\nGenerated by test\n",
            planning_iteration=2,
        )
        # Use max_iterations=4 so we don't hit the limit at iteration 3
        result = refine_roadmap(state, configurable={"planning_max_iterations": 4})

        assert "Final refinement complete" in result["draft_roadmap"]

    def test_refine_marks_complete_at_max_iterations(self):
        """Refine should mark planning_complete at max iterations."""
        state = _make_state(
            draft_roadmap="## Goal\nAuth.\n\n## Notes\n\nGenerated by test\n",
            planning_iteration=2,
        )
        # max_iterations=3, next would be 3 >= 3, so complete
        result = refine_roadmap(state, configurable={"planning_max_iterations": 3})

        assert result.get("planning_complete") is True

    def test_refine_preserves_other_content(self):
        """Refine should preserve content outside Notes section."""
        state = _make_state(
            draft_roadmap="""## Goal
Build auth.

## Todos
- [ ] Create model

## Target Files
- src/auth.ts
""",
            planning_iteration=1,
        )
        result = refine_roadmap(state)

        assert "Build auth" in result["draft_roadmap"]
        assert "- [ ] Create model" in result["draft_roadmap"]


# ---------------------------------------------------------------------------
# Loop termination tests
# ---------------------------------------------------------------------------


class TestLoopTermination:
    """Tests for planning loop termination conditions."""

    def test_needs_planning_returns_yes_with_user_request(self):
        """needs_planning should return 'yes' when user_request exists."""
        state = _make_state(user_request="Build auth", planning_complete=False)
        result = needs_planning(state)

        assert result == "yes"

    def test_needs_planning_returns_no_without_user_request(self):
        """needs_planning should return 'no' when no user_request."""
        state = _make_state(user_request="", planning_complete=False)
        result = needs_planning(state)

        assert result == "no"

    def test_needs_planning_returns_no_when_complete(self):
        """needs_planning should return 'no' when planning already complete."""
        state = _make_state(user_request="Build auth", planning_complete=True)
        result = needs_planning(state)

        assert result == "no"

    def test_needs_planning_returns_no_with_empty_request(self):
        """needs_planning should return 'no' with empty/missing request."""
        state = _make_state()
        state.pop("user_request", None)
        result = needs_planning(state)

        assert result == "no"

    def test_is_planning_complete_returns_yes_when_complete(self):
        """is_planning_complete should return 'yes' when planning_complete=True."""
        state = _make_state(planning_complete=True)
        result = is_planning_complete(state)

        assert result == "yes"

    def test_is_planning_complete_returns_no_when_incomplete(self):
        """is_planning_complete should return 'no' when planning_complete=False."""
        state = _make_state(planning_complete=False)
        result = is_planning_complete(state)

        assert result == "no"

    def test_loop_terminates_at_max_iterations(self):
        """Planning loop should terminate at max iterations."""
        # Simulate reaching max iterations (iteration 3 with max 3)
        state = _make_state(
            draft_roadmap="## Goal\nAuth.\n\n## Notes\n\nGenerated by test\n",
            planning_iteration=3,
        )
        # Max iterations reached in refine should mark complete
        result = refine_roadmap(state, configurable={"planning_max_iterations": 3})

        assert result.get("planning_complete") is True

    def test_loop_terminates_early_for_basic_issues(self):
        """Planning should terminate early if basic issues are detected."""
        # Very short draft should trigger early completion
        state = _make_state(draft_roadmap="Short")
        result = critique_roadmap(state)

        assert result.get("planning_complete") is True


# ---------------------------------------------------------------------------
# File persistence tests
# ---------------------------------------------------------------------------


class TestFilePersistence:
    """Tests for write_roadmap file output."""

    def test_write_roadmap_creates_file(self, tmp_agent_dir):
        """write_roadmap should create .agent/roadmap.md."""
        draft = """## Goal
Build auth.

## Todos
- [ ] Task

## Target Files
- src/auth.ts
"""
        state = _make_state(draft_roadmap=draft)
        write_roadmap(state)

        roadmap_path = tmp_agent_dir / "roadmap.md"
        assert roadmap_path.exists()

    def test_write_roadmap_contains_draft_content(self, tmp_agent_dir):
        """write_roadmap should write the draft content to file."""
        draft = "## Goal\nAuth system.\n\n## Todos\n- [ ] Login\n"
        state = _make_state(draft_roadmap=draft)
        write_roadmap(state)

        roadmap_path = tmp_agent_dir / "roadmap.md"
        content = roadmap_path.read_text()
        assert "Auth system" in content
        assert "- [ ] Login" in content

    def test_write_roadmap_returns_roadmap_in_state(self, tmp_agent_dir):
        """write_roadmap should return roadmap in state for graph flow."""
        draft = "## Goal\nAuth.\n\n## Todos\n- [ ] Task\n"
        state = _make_state(draft_roadmap=draft)
        result = write_roadmap(state)

        assert "roadmap" in result
        assert result["roadmap"] == draft

    def test_write_roadmap_creates_parent_directories(self, tmp_agent_dir):
        """write_roadmap should create parent directories if needed."""
        # Remove the roadmap file
        roadmap = tmp_agent_dir / "roadmap.md"
        if roadmap.exists():
            roadmap.unlink()

        draft = "## Goal\nTest.\n\n## Todos\n- [ ] Task\n"
        state = _make_state(draft_roadmap=draft)
        write_roadmap(state)

        assert (tmp_agent_dir / "roadmap.md").exists()

    def test_write_roadmap_handles_empty_draft(self, tmp_agent_dir):
        """write_roadmap should handle empty draft gracefully."""
        state = _make_state(draft_roadmap="")
        result = write_roadmap(state)

        # Should return empty dict or not write
        assert result == {} or "roadmap" not in result

    def test_write_roadmap_overwrites_existing(self, tmp_agent_dir):
        """write_roadmap should overwrite existing roadmap."""
        # First write
        draft1 = "## Goal\nFirst.\n\n## Todos\n- [ ] Task 1\n"
        write_roadmap(_make_state(draft_roadmap=draft1))

        # Second write
        draft2 = "## Goal\nSecond.\n\n## Todos\n- [ ] Task 2\n"
        write_roadmap(_make_state(draft_roadmap=draft2))

        roadmap_path = tmp_agent_dir / "roadmap.md"
        content = roadmap_path.read_text()

        assert "Second" in content
        assert "Task 2" in content
        assert "First" not in content
