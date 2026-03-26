"""Tests for planning loop nodes in src/sebba_code/nodes/planning.py."""

from unittest.mock import MagicMock

import pytest

from sebba_code.nodes.planning import (
    is_planning_complete,
    plan_critique,
    plan_draft,
    plan_refine,
)
from sebba_code.nodes.approval import build_dag


def _make_state(**overrides) -> dict:
    """Create a minimal valid state dict with planning fields."""
    state = {
        "messages": [],
        "target_files": [],
        "briefing": "",
        "memory": {
            "l0_index": "",
            "l1_files": {},
            "l2_files": {},
            "active_rules": {},
            "session_history": "",
        },
        "working_branch": None,
        "user_request": "Build auth system",
        "draft_plan": "",
        "planning_messages": [],
        "planning_iteration": 0,
        "planning_complete": False,
        "rejection_reason": "",
        "tasks": {},
        "task_results": [],
        "tasks_completed_this_session": [],
        "plan_approved": None,
    }
    state.update(overrides)
    return state


SAMPLE_PLAN_JSON = """{
  "tasks": [
    {"id": "task-001", "description": "Create user model", "depends_on": [], "target_files": ["src/models/user.py"]},
    {"id": "task-002", "description": "Add login endpoint", "depends_on": ["task-001"], "target_files": ["src/api/auth.py"]},
    {"id": "task-003", "description": "Write auth tests", "depends_on": ["task-002"], "target_files": ["tests/test_auth.py"]}
  ]
}"""


class TestPlanDraft:
    """Tests for plan_draft output."""

    def test_draft_returns_plan_content(self, monkeypatch):
        mock_llm = MagicMock()
        mock_response = MagicMock()
        mock_response.content = SAMPLE_PLAN_JSON
        mock_llm.invoke.return_value = mock_response
        monkeypatch.setattr("sebba_code.nodes.planning.get_llm", lambda **kw: mock_llm)

        state = _make_state()
        result = plan_draft(state)

        assert "draft_plan" in result
        assert "tasks" in result["draft_plan"]

    def test_draft_sets_iteration_to_1(self, monkeypatch):
        mock_llm = MagicMock()
        mock_response = MagicMock()
        mock_response.content = SAMPLE_PLAN_JSON
        mock_llm.invoke.return_value = mock_response
        monkeypatch.setattr("sebba_code.nodes.planning.get_llm", lambda **kw: mock_llm)

        state = _make_state(planning_iteration=0)
        result = plan_draft(state)

        assert result["planning_iteration"] == 1

    def test_draft_uses_user_request(self, monkeypatch):
        mock_llm = MagicMock()
        mock_response = MagicMock()
        mock_response.content = SAMPLE_PLAN_JSON
        mock_llm.invoke.return_value = mock_response
        monkeypatch.setattr("sebba_code.nodes.planning.get_llm", lambda **kw: mock_llm)

        state = _make_state(user_request="Build OAuth2 login")
        plan_draft(state)

        assert mock_llm.invoke.called


class TestPlanCritique:
    """Tests for plan_critique validation logic."""

    def test_detects_missing_tasks(self):
        state = _make_state(draft_plan="No tasks here")
        result = plan_critique(state)
        # Issues found on iteration 0 triggers a refine cycle
        assert result.get("planning_complete") is False
        assert "rejection_reason" in result

    def test_detects_short_content(self):
        state = _make_state(draft_plan="short")
        result = plan_critique(state)
        # Issues found on iteration 0 triggers a refine cycle
        assert result.get("planning_complete") is False
        assert "rejection_reason" in result

    def test_issues_at_max_iterations_accepts(self):
        """When issues are found but max iterations reached, accept anyway."""
        state = _make_state(draft_plan="short", planning_iteration=2)
        result = plan_critique(state)
        assert result.get("planning_complete") is True

    def test_passes_valid_plan(self):
        state = _make_state(draft_plan=SAMPLE_PLAN_JSON)
        result = plan_critique(state)
        assert result.get("planning_complete") is True

    def test_respects_max_iterations(self):
        state = _make_state(draft_plan=SAMPLE_PLAN_JSON, planning_iteration=2)
        result = plan_critique(state, configurable={"planning_max_iterations": 2})
        assert result.get("planning_complete") is True


class TestPlanRefine:
    """Tests for plan_refine."""

    def test_increments_iteration(self):
        state = _make_state(draft_plan=SAMPLE_PLAN_JSON, planning_iteration=1)
        result = plan_refine(state, configurable={"planning_max_iterations": 5})
        assert result["planning_iteration"] == 2

    def test_marks_complete_at_max(self):
        state = _make_state(draft_plan=SAMPLE_PLAN_JSON, planning_iteration=2)
        result = plan_refine(state, configurable={"planning_max_iterations": 3})
        assert result.get("planning_complete") is True


class TestIsComplete:
    """Tests for is_planning_complete router."""

    def test_returns_yes_when_complete(self):
        state = _make_state(planning_complete=True)
        assert is_planning_complete(state) == "yes"

    def test_returns_no_when_incomplete(self):
        state = _make_state(planning_complete=False)
        assert is_planning_complete(state) == "no"


class TestBuildDag:
    """Tests for build_dag node."""

    def test_parses_tasks_from_json(self):
        state = _make_state(draft_plan=SAMPLE_PLAN_JSON)
        result = build_dag(state)

        tasks = result["tasks"]
        assert len(tasks) == 3
        assert "task-001" in tasks
        assert "task-002" in tasks
        assert "task-003" in tasks

    def test_task_dependencies(self):
        state = _make_state(draft_plan=SAMPLE_PLAN_JSON)
        result = build_dag(state)

        tasks = result["tasks"]
        assert tasks["task-001"]["depends_on"] == []
        assert tasks["task-002"]["depends_on"] == ["task-001"]
        assert tasks["task-003"]["depends_on"] == ["task-002"]

    def test_tasks_start_pending(self):
        state = _make_state(draft_plan=SAMPLE_PLAN_JSON)
        result = build_dag(state)

        for task in result["tasks"].values():
            assert task["status"] == "pending"

    def test_task_target_files(self):
        state = _make_state(draft_plan=SAMPLE_PLAN_JSON)
        result = build_dag(state)

        assert result["tasks"]["task-001"]["target_files"] == ["src/models/user.py"]

    def test_empty_plan(self):
        state = _make_state(draft_plan="")
        result = build_dag(state)
        assert result["tasks"] == {}
