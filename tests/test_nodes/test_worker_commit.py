"""Tests for the worker commit step in the task worker subgraph."""

import subprocess
from unittest.mock import MagicMock, patch

import pytest

from sebba_code.nodes.worker import _should_commit, worker_commit_changes
from sebba_code.state import TaskResult


def _make_task_result(**overrides) -> TaskResult:
    base = TaskResult(
        task_id="task-001",
        summary="Added auth module",
        what_i_did="- Created src/auth.py",
        decisions_made="",
        files_touched="src/auth.py",
        dag_mutations=[],
        memory_updates={},
        commit_sha="",
    )
    base.update(overrides)
    return base


def _make_worker_state(**overrides) -> dict:
    state = {
        "task": {
            "id": "task-001",
            "description": "Create auth module",
            "status": "running",
            "depends_on": [],
            "blocked_reason": "",
            "result_summary": "",
            "files_touched": [],
            "target_files": ["src/auth.py"],
            "progress_summary": "",
        },
        "messages": [],
        "worker_briefing": "",
        "predecessor_context": "",
        "memory": {
            "l0_index": "",
            "l1_files": {},
            "l2_files": {},
            "active_rules": {},
            "session_history": "",
        },
        "target_files": ["src/auth.py"],
        "working_branch": None,
        "task_result": _make_task_result(),
        "task_results": [],
    }
    state.update(overrides)
    return state


class TestShouldCommit:
    """Tests for _should_commit routing function."""

    def test_never_mode_skips_commit(self, monkeypatch):
        config = MagicMock()
        config.execution.auto_commit = "never"
        monkeypatch.setattr(
            "sebba_code.config.load_config", lambda _: config
        )
        state = _make_worker_state()
        assert _should_commit(state) == "extract_memory"

    def test_always_mode_commits(self, monkeypatch):
        config = MagicMock()
        config.execution.auto_commit = "always"
        monkeypatch.setattr(
            "sebba_code.config.load_config", lambda _: config
        )
        state = _make_worker_state()
        assert _should_commit(state) == "commit_changes"

    def test_auto_mode_commits_when_files_touched(self, monkeypatch):
        config = MagicMock()
        config.execution.auto_commit = "auto"
        monkeypatch.setattr(
            "sebba_code.config.load_config", lambda _: config
        )
        state = _make_worker_state()
        assert _should_commit(state) == "commit_changes"

    def test_auto_mode_skips_when_no_files_touched(self, monkeypatch):
        config = MagicMock()
        config.execution.auto_commit = "auto"
        monkeypatch.setattr(
            "sebba_code.config.load_config", lambda _: config
        )
        state = _make_worker_state(task_result=_make_task_result(files_touched=""))
        assert _should_commit(state) == "extract_memory"

    def test_skips_when_task_blocked(self, monkeypatch):
        config = MagicMock()
        config.execution.auto_commit = "auto"
        monkeypatch.setattr(
            "sebba_code.config.load_config", lambda _: config
        )
        result = _make_task_result(
            files_touched="src/auth.py",
            dag_mutations=[{"type": "add_blocking_task", "description": "need DB first"}],
        )
        state = _make_worker_state(task_result=result)
        assert _should_commit(state) == "extract_memory"

    def test_skips_when_no_task_result(self, monkeypatch):
        config = MagicMock()
        config.execution.auto_commit = "auto"
        monkeypatch.setattr(
            "sebba_code.config.load_config", lambda _: config
        )
        state = _make_worker_state(task_result=None)
        assert _should_commit(state) == "extract_memory"

    def test_defaults_to_auto_on_config_error(self, monkeypatch):
        monkeypatch.setattr(
            "sebba_code.config.load_config", MagicMock(side_effect=Exception("no config"))
        )
        state = _make_worker_state()
        assert _should_commit(state) == "commit_changes"

    def test_always_mode_skips_when_blocked(self, monkeypatch):
        config = MagicMock()
        config.execution.auto_commit = "always"
        monkeypatch.setattr(
            "sebba_code.config.load_config", lambda _: config
        )
        result = _make_task_result(
            dag_mutations=[{"type": "add_blocking_task", "description": "prereq"}],
        )
        state = _make_worker_state(task_result=result)
        assert _should_commit(state) == "extract_memory"

    def test_auto_ignores_non_blocking_mutations(self, monkeypatch):
        config = MagicMock()
        config.execution.auto_commit = "auto"
        monkeypatch.setattr(
            "sebba_code.config.load_config", lambda _: config
        )
        result = _make_task_result(
            files_touched="src/auth.py",
            dag_mutations=[{"type": "add_subtask", "description": "extra work"}],
        )
        state = _make_worker_state(task_result=result)
        assert _should_commit(state) == "commit_changes"


class TestWorkerCommitChanges:
    """Tests for worker_commit_changes node function."""

    def test_commits_files_from_task_result(self, monkeypatch):
        add_calls = []
        commit_calls = []

        def mock_git_run(args, **kwargs):
            result = MagicMock()
            result.returncode = 0
            result.stdout = ""
            result.stderr = ""
            if args[0] == "add":
                add_calls.append(args[1])
            elif args[0] == "commit":
                commit_calls.append(args)
                result.stdout = "[main abc1234] chore: test"
            elif args[0] == "rev-parse":
                result.stdout = "abc1234"
            return result

        mock_llm = MagicMock()
        mock_response = MagicMock()
        mock_response.content = '{"type": "feat", "scope": "auth", "description": "add auth module"}'
        mock_llm.return_value = mock_response

        monkeypatch.setattr("sebba_code.helpers.git.git_run", mock_git_run)
        monkeypatch.setattr("sebba_code.nodes.worker.invoke_with_timeout", lambda llm, prompt: mock_response)
        monkeypatch.setattr("sebba_code.nodes.worker.get_cheap_llm", lambda: mock_llm)

        state = _make_worker_state()
        result = worker_commit_changes(state)

        assert result["task_result"]["commit_sha"] == "abc1234"
        assert "src/auth.py" in add_calls
        assert len(commit_calls) == 1

    def test_returns_empty_when_no_task_result(self):
        state = _make_worker_state(task_result=None)
        result = worker_commit_changes(state)
        assert result == {}

    def test_falls_back_to_git_diff_when_no_files_touched(self, monkeypatch):
        add_calls = []

        def mock_git_run(args, **kwargs):
            result = MagicMock()
            result.returncode = 0
            result.stdout = ""
            result.stderr = ""
            if args[0] == "diff" and "--name-only" in args:
                result.stdout = "src/detected.py\n"
            elif args[0] == "add":
                add_calls.append(args[1])
            elif args[0] == "rev-parse":
                result.stdout = "def5678"
            return result

        mock_response = MagicMock()
        mock_response.content = '{"type": "chore", "scope": "", "description": "update detected file"}'

        monkeypatch.setattr("sebba_code.helpers.git.git_run", mock_git_run)
        monkeypatch.setattr("sebba_code.nodes.worker.invoke_with_timeout", lambda llm, prompt: mock_response)
        monkeypatch.setattr("sebba_code.nodes.worker.get_cheap_llm", lambda: MagicMock())

        state = _make_worker_state(task_result=_make_task_result(files_touched=""))
        result = worker_commit_changes(state)

        assert "src/detected.py" in add_calls

    def test_skips_commit_when_no_changes_detected(self, monkeypatch):
        def mock_git_run(args, **kwargs):
            result = MagicMock()
            result.returncode = 0
            result.stdout = ""
            result.stderr = ""
            return result

        monkeypatch.setattr("sebba_code.helpers.git.git_run", mock_git_run)

        state = _make_worker_state(task_result=_make_task_result(files_touched=""))
        result = worker_commit_changes(state)

        assert result["task_result"]["commit_sha"] == ""

    def test_handles_commit_failure_gracefully(self, monkeypatch):
        def mock_git_run(args, **kwargs):
            result = MagicMock()
            result.returncode = 0
            result.stdout = ""
            result.stderr = ""
            if args[0] == "commit":
                result.returncode = 1
                result.stderr = "nothing to commit"
            return result

        mock_response = MagicMock()
        mock_response.content = '{"type": "feat", "scope": "", "description": "test"}'

        monkeypatch.setattr("sebba_code.helpers.git.git_run", mock_git_run)
        monkeypatch.setattr("sebba_code.nodes.worker.invoke_with_timeout", lambda llm, prompt: mock_response)
        monkeypatch.setattr("sebba_code.nodes.worker.get_cheap_llm", lambda: MagicMock())

        state = _make_worker_state()
        result = worker_commit_changes(state)

        assert result["task_result"]["commit_sha"] == ""

    def test_uses_fallback_message_when_llm_fails(self, monkeypatch):
        commit_messages = []

        def mock_git_run(args, **kwargs):
            result = MagicMock()
            result.returncode = 0
            result.stdout = ""
            result.stderr = ""
            if args[0] == "commit":
                commit_messages.append(args[2])  # -m <message>
            elif args[0] == "rev-parse":
                result.stdout = "aaa1111"
            return result

        monkeypatch.setattr("sebba_code.helpers.git.git_run", mock_git_run)
        monkeypatch.setattr(
            "sebba_code.nodes.worker.invoke_with_timeout",
            MagicMock(side_effect=Exception("LLM down")),
        )
        monkeypatch.setattr("sebba_code.nodes.worker.get_cheap_llm", lambda: MagicMock())

        state = _make_worker_state()
        result = worker_commit_changes(state)

        assert result["task_result"]["commit_sha"] == "aaa1111"
        assert len(commit_messages) == 1
        assert commit_messages[0].startswith("chore: ")

    def test_handles_multiple_files(self, monkeypatch):
        add_calls = []

        def mock_git_run(args, **kwargs):
            result = MagicMock()
            result.returncode = 0
            result.stdout = ""
            result.stderr = ""
            if args[0] == "add":
                add_calls.append(args[1])
            elif args[0] == "rev-parse":
                result.stdout = "bbb2222"
            return result

        mock_response = MagicMock()
        mock_response.content = '{"type": "feat", "scope": "auth", "description": "add auth"}'

        monkeypatch.setattr("sebba_code.helpers.git.git_run", mock_git_run)
        monkeypatch.setattr("sebba_code.nodes.worker.invoke_with_timeout", lambda llm, prompt: mock_response)
        monkeypatch.setattr("sebba_code.nodes.worker.get_cheap_llm", lambda: MagicMock())

        task_result = _make_task_result(files_touched="src/auth.py, src/models/user.py, tests/test_auth.py")
        state = _make_worker_state(task_result=task_result)
        result = worker_commit_changes(state)

        assert set(add_calls) == {"src/auth.py", "src/models/user.py", "tests/test_auth.py"}

    def test_uses_conventional_commit_format(self, monkeypatch):
        commit_messages = []

        def mock_git_run(args, **kwargs):
            result = MagicMock()
            result.returncode = 0
            result.stdout = ""
            result.stderr = ""
            if args[0] == "commit":
                commit_messages.append(args[2])
            elif args[0] == "rev-parse":
                result.stdout = "ccc3333"
            return result

        mock_result = {"type": "feat", "scope": "auth", "description": "add OAuth2 support"}

        monkeypatch.setattr("sebba_code.helpers.git.git_run", mock_git_run)
        monkeypatch.setattr("sebba_code.nodes.worker.invoke_with_timeout", lambda llm, prompt: mock_result)
        monkeypatch.setattr("sebba_code.nodes.worker.get_cheap_llm", lambda: MagicMock())

        state = _make_worker_state()
        result = worker_commit_changes(state)

        assert commit_messages[0] == "feat(auth): add OAuth2 support"


class TestWorkerToolsExcludeGitCommit:
    """Verify git_commit is no longer in worker tools."""

    def test_git_commit_not_in_worker_tools(self):
        from sebba_code.tools import get_worker_tools
        tool_names = [t.name for t in get_worker_tools()]
        assert "git_commit" not in tool_names

    def test_git_commit_still_in_all_tools(self):
        from sebba_code.tools import get_all_tools
        tool_names = [t.name for t in get_all_tools()]
        assert "git_commit" in tool_names


class TestAutoCommitConfig:
    """Tests for the auto_commit config field."""

    def test_default_value(self):
        from sebba_code.config import ExecutionConfig
        config = ExecutionConfig()
        assert config.auto_commit == "auto"

    def test_can_set_to_never(self):
        from sebba_code.config import ExecutionConfig
        config = ExecutionConfig(auto_commit="never")
        assert config.auto_commit == "never"

    def test_can_set_to_always(self):
        from sebba_code.config import ExecutionConfig
        config = ExecutionConfig(auto_commit="always")
        assert config.auto_commit == "always"
