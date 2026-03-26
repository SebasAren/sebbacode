"""Tests for planning loop nodes in src/sebba_code/nodes/planning.py."""

from unittest.mock import MagicMock

import pytest

from sebba_code.nodes.planning import (
    _check_unnecessary_delegation,
    _is_explore_task,
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


class TestIsExploreTask:
    """Tests for the _is_explore_task helper function."""

    def test_explore_keyword(self):
        assert _is_explore_task("Explore existing auth patterns") is True
        assert _is_explore_task("Explore the codebase structure") is True

    def test_investigate_keyword(self):
        assert _is_explore_task("Investigate current implementation") is True
        assert _is_explore_task("Investigate where sessions are stored") is True

    def test_find_patterns(self):
        assert _is_explore_task("Find where the user model is defined") is True
        assert _is_explore_task("Find what patterns exist for caching") is True

    def test_discover_keyword(self):
        assert _is_explore_task("Discover existing API endpoints") is True

    def test_understand_keyword(self):
        assert _is_explore_task("Understand the current architecture") is True

    def test_analyze_patterns(self):
        assert _is_explore_task("Analyze codebase structure") is True
        assert _is_explore_task("Analyze existing patterns") is True

    def test_check_patterns(self):
        assert _is_explore_task("Check existing implementations") is True
        assert _is_explore_task("Check where the database is configured") is True

    def test_look_patterns(self):
        assert _is_explore_task("Look at the current test setup") is True
        assert _is_explore_task("Look into error handling patterns") is True

    def test_examine_keyword(self):
        assert _is_explore_task("Examine the current middleware") is True

    def test_locate_keyword(self):
        assert _is_explore_task("Locate configuration files") is True

    def test_identify_patterns(self):
        assert _is_explore_task("Identify where caching happens") is True
        assert _is_explore_task("Identify what files need updating") is True

    def test_see_patterns(self):
        assert _is_explore_task("See how the router is configured") is True
        assert _is_explore_task("See what dependencies exist") is True

    def test_case_insensitive(self):
        assert _is_explore_task("EXPLORE the codebase") is True
        assert _is_explore_task("Explore") is True

    def test_non_explore_tasks(self):
        """Regular implementation tasks should not be flagged."""
        assert _is_explore_task("Create the user model") is False
        assert _is_explore_task("Add login endpoint to API") is False
        assert _is_explore_task("Write unit tests for auth") is False
        assert _is_explore_task("Implement JWT token generation") is False
        assert _is_explore_task("Refactor the session handling") is False
        assert _is_explore_task("Update the configuration file") is False


class TestCheckUnnecessaryDelegation:
    """Tests for the _check_unnecessary_delegation helper function."""

    def test_flags_explore_tasks(self):
        tasks = [
            {"id": "task-001", "description": "Explore existing patterns", "depends_on": []},
            {"id": "task-002", "description": "Create user model", "depends_on": []},
        ]
        flagged = _check_unnecessary_delegation(tasks)
        assert "task-001" in flagged
        assert "task-002" not in flagged

    def test_no_flags_for_regular_tasks(self):
        tasks = [
            {"id": "task-001", "description": "Create the database schema", "depends_on": []},
            {"id": "task-002", "description": "Add API endpoint", "depends_on": ["task-001"]},
        ]
        flagged = _check_unnecessary_delegation(tasks)
        assert flagged == []

    def test_empty_tasks_list(self):
        flagged = _check_unnecessary_delegation([])
        assert flagged == []

    def test_multiple_explore_tasks(self):
        tasks = [
            {"id": "task-001", "description": "Explore codebase structure", "depends_on": []},
            {"id": "task-002", "description": "Investigate existing patterns", "depends_on": []},
            {"id": "task-003", "description": "Implement the feature", "depends_on": []},
        ]
        flagged = _check_unnecessary_delegation(tasks)
        assert len(flagged) == 2
        assert "task-001" in flagged
        assert "task-002" in flagged
        assert "task-003" not in flagged

    def test_missing_description(self):
        """Tasks without description should not be flagged."""
        tasks = [{"id": "task-001", "depends_on": []}]
        flagged = _check_unnecessary_delegation(tasks)
        assert flagged == []


class TestPlanCritiqueUnnecessaryDelegation:
    """Tests for plan_critique integration with unnecessary delegation check."""

    def test_flags_explore_tasks_in_plan(self):
        """Explore tasks in plan should cause rejection."""
        plan_with_explore = """{
          "tasks": [
            {"id": "task-001", "description": "Explore existing auth patterns", "depends_on": [], "target_files": []},
            {"id": "task-002", "description": "Create user model", "depends_on": [], "target_files": ["src/models/user.py"]}
          ]
        }"""
        state = _make_state(draft_plan=plan_with_explore)
        result = plan_critique(state)

        assert result.get("planning_complete") is False
        assert "rejection_reason" in result
        assert "task-001" in result["rejection_reason"]
        assert "Explore tasks should be done by the planner directly" in result["rejection_reason"]

    def test_accepts_plan_without_explore_tasks(self):
        """Plan without explore tasks should pass critique."""
        state = _make_state(draft_plan=SAMPLE_PLAN_JSON)
        result = plan_critique(state)

        assert result.get("planning_complete") is True

    def test_investigate_task_flagged(self):
        """Investigate tasks should be flagged."""
        plan = """{
          "tasks": [
            {"id": "task-001", "description": "Investigate current session handling", "depends_on": [], "target_files": []}
          ]
        }"""
        state = _make_state(draft_plan=plan)
        result = plan_critique(state)

        assert result.get("planning_complete") is False
        assert "task-001" in result["rejection_reason"]

    def test_multiple_explore_tasks_all_flagged(self):
        """Multiple explore tasks should all be mentioned in rejection."""
        plan = """{
          "tasks": [
            {"id": "task-001", "description": "Explore the database schema", "depends_on": [], "target_files": []},
            {"id": "task-002", "description": "Find where caching is implemented", "depends_on": [], "target_files": []}
          ]
        }"""
        state = _make_state(draft_plan=plan)
        result = plan_critique(state)

        assert result.get("planning_complete") is False
        assert "task-001" in result["rejection_reason"]
        assert "task-002" in result["rejection_reason"]

    def test_empty_tasks_array(self):
        """Plan with empty tasks should fail basic validation, not delegation check."""
        plan = '{"tasks": []}'
        state = _make_state(draft_plan=plan)
        result = plan_critique(state)

        # Empty tasks fails structure check
        assert result.get("planning_complete") is False
        assert "rejection_reason" in result


class TestExploreToolPreference:
    """Tests verifying planner prefers direct explore tool over subagent exploration.

    These tests validate that:
    1. Explore tasks in plans are rejected (they should be done directly via explore_codebase)
    2. Plans without explore tasks are accepted
    3. The critique message instructs the planner to run explore tool directly
    """

    def test_rejects_explore_task_suggests_direct_tool(self):
        """Plans with explore tasks should be rejected with suggestion to use explore_codebase."""
        plan = """{
          "tasks": [
            {"id": "task-001", "description": "Explore existing API patterns", "depends_on": [], "target_files": []}
          ]
        }"""
        state = _make_state(draft_plan=plan)
        result = plan_critique(state)

        # Plan should be rejected
        assert result.get("planning_complete") is False

        # Rejection reason should mention explore_codebase
        assert "rejection_reason" in result
        assert "explore_codebase" in result["rejection_reason"].lower()
        assert "task-001" in result["rejection_reason"]

    def test_rejects_investigate_task_suggests_direct_tool(self):
        """Investigate tasks should be rejected with suggestion to use explore tool."""
        plan = """{
          "tasks": [
            {"id": "task-001", "description": "Investigate the session management code", "depends_on": [], "target_files": []}
          ]
        }"""
        state = _make_state(draft_plan=plan)
        result = plan_critique(state)

        assert result.get("planning_complete") is False
        assert "explore_codebase" in result["rejection_reason"].lower()

    def test_rejects_find_pattern_task(self):
        """Find-pattern tasks should be rejected - planner should use explore directly."""
        plan = """{
          "tasks": [
            {"id": "task-001", "description": "Find where authentication is handled", "depends_on": [], "target_files": []}
          ]
        }"""
        state = _make_state(draft_plan=plan)
        result = plan_critique(state)

        assert result.get("planning_complete") is False
        assert "task-001" in result["rejection_reason"]

    def test_accepts_plan_without_explore_tasks_preferring_direct_tool(self):
        """Plans without explore tasks should be accepted - confirming direct tool preference."""
        # This plan has no explore tasks - it should pass critique
        plan = """{
          "tasks": [
            {"id": "task-001", "description": "Create user authentication module", "depends_on": [], "target_files": ["src/auth/user.py"]},
            {"id": "task-002", "description": "Add login endpoint to API", "depends_on": ["task-001"], "target_files": ["src/api/auth.py"]}
          ]
        }"""
        state = _make_state(draft_plan=plan)
        result = plan_critique(state)

        # Plan without explore tasks should pass
        assert result.get("planning_complete") is True

    def test_rejects_mixed_plan_with_explore_tasks(self):
        """Mixed plans with any explore tasks should be rejected."""
        plan = """{
          "tasks": [
            {"id": "task-001", "description": "Create user authentication module", "depends_on": [], "target_files": ["src/auth/user.py"]},
            {"id": "task-002", "description": "Explore current session handling", "depends_on": [], "target_files": []},
            {"id": "task-003", "description": "Add JWT token generation", "depends_on": ["task-001"], "target_files": ["src/auth/tokens.py"]}
          ]
        }"""
        state = _make_state(draft_plan=plan)
        result = plan_critique(state)

        # Mixed plan with explore task should be rejected
        assert result.get("planning_complete") is False
        assert "task-002" in result["rejection_reason"]
        # task-001 and task-003 should not be flagged
        assert "task-001" not in result["rejection_reason"]
        assert "task-003" not in result["rejection_reason"]

    def test_rejects_analyze_task_suggests_direct_explore(self):
        """Analyze-codebase tasks should be rejected - planner should use explore."""
        plan = """{
          "tasks": [
            {"id": "task-001", "description": "Analyze codebase structure for patterns", "depends_on": [], "target_files": []}
          ]
        }"""
        state = _make_state(draft_plan=plan)
        result = plan_critique(state)

        assert result.get("planning_complete") is False
        assert "explore_codebase" in result["rejection_reason"].lower()

    def test_rejects_discover_task(self):
        """Discover tasks should be rejected - planner should use explore directly."""
        plan = """{
          "tasks": [
            {"id": "task-001", "description": "Discover existing caching implementations", "depends_on": [], "target_files": []}
          ]
        }"""
        state = _make_state(draft_plan=plan)
        result = plan_critique(state)

        assert result.get("planning_complete") is False
        assert "task-001" in result["rejection_reason"]

    def test_rejects_understand_task(self):
        """Understand tasks should be rejected - planner should use explore directly."""
        plan = """{
          "tasks": [
            {"id": "task-001", "description": "Understand the current architecture", "depends_on": [], "target_files": []}
          ]
        }"""
        state = _make_state(draft_plan=plan)
        result = plan_critique(state)

        assert result.get("planning_complete") is False
        assert "task-001" in result["rejection_reason"]

    def test_rejects_examine_task(self):
        """Examine tasks should be rejected - planner should use explore directly."""
        plan = """{
          "tasks": [
            {"id": "task-001", "description": "Examine the error handling patterns", "depends_on": [], "target_files": []}
          ]
        }"""
        state = _make_state(draft_plan=plan)
        result = plan_critique(state)

        assert result.get("planning_complete") is False
        assert "task-001" in result["rejection_reason"]

    def test_rejects_look_at_task(self):
        """Look-at tasks should be rejected - planner should use explore directly."""
        plan = """{
          "tasks": [
            {"id": "task-001", "description": "Look at the test setup", "depends_on": [], "target_files": []}
          ]
        }"""
        state = _make_state(draft_plan=plan)
        result = plan_critique(state)

        assert result.get("planning_complete") is False
        assert "task-001" in result["rejection_reason"]

    def test_iteration_increments_on_explore_task_rejection(self):
        """Explore task rejection should increment planning iteration."""
        plan = """{
          "tasks": [
            {"id": "task-001", "description": "Explore the codebase", "depends_on": [], "target_files": []}
          ]
        }"""
        state = _make_state(draft_plan=plan, planning_iteration=1)
        result = plan_critique(state)

        # Should be rejected with incremented iteration
        assert result.get("planning_complete") is False
        assert result.get("planning_iteration") == 2

    def test_direct_explore_tool_preserves_valid_implementation_tasks(self):
        """Plans with only implementation tasks should be accepted."""
        plan = """{
          "tasks": [
            {"id": "task-001", "description": "Create database migration for users", "depends_on": [], "target_files": ["migrations/001_users.sql"]},
            {"id": "task-002", "description": "Implement user registration endpoint", "depends_on": ["task-001"], "target_files": ["src/api/users.py"]},
            {"id": "task-003", "description": "Write unit tests for registration", "depends_on": ["task-002"], "target_files": ["tests/test_registration.py"]}
          ]
        }"""
        state = _make_state(draft_plan=plan)
        result = plan_critique(state)

        # Implementation-only plan should pass
        assert result.get("planning_complete") is True

    def test_planner_should_not_delegate_exploration_to_subagent(self):
        """This test verifies the core principle: exploration should be done directly.

        The critique message explicitly states: 'run explore_codebase before creating tasks'
        This confirms the planner should NOT delegate exploration to subagents.
        """
        plan = """{
          "tasks": [
            {"id": "task-001", "description": "Explore existing auth patterns", "depends_on": [], "target_files": []},
            {"id": "task-002", "description": "Create auth module", "depends_on": ["task-001"], "target_files": ["src/auth.py"]}
          ]
        }"""
        state = _make_state(draft_plan=plan)
        result = plan_critique(state)

        # Rejection should explicitly mention running explore tool directly
        assert result.get("planning_complete") is False
        rejection = result["rejection_reason"]
        assert "explore_codebase" in rejection.lower()
        assert "directly" in rejection.lower()


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

        state = _make_state(user_request="Build a payment system")
        result = plan_draft(state)

        assert "draft_plan" in result

    def test_draft_includes_explore_directive_in_prompt(self, monkeypatch):
        """Verify the draft prompt includes the explore_codebase directive."""
        captured_prompts = []

        def mock_invoke(prompt):
            captured_prompts.append(prompt)
            mock_response = MagicMock()
            mock_response.content = SAMPLE_PLAN_JSON
            return mock_response

        mock_llm = MagicMock()
        mock_llm.invoke.side_effect = mock_invoke
        monkeypatch.setattr("sebba_code.nodes.planning.get_llm", lambda **kw: mock_llm)

        state = _make_state()
        plan_draft(state)

        # Verify the prompt contains the explore directive
        assert len(captured_prompts) == 1
        prompt = captured_prompts[0]
        assert "explore_codebase" in prompt
        assert "Explore Before Planning" in prompt


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
