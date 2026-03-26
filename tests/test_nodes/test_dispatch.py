"""Tests for task dispatch and DAG execution logic."""

import pytest

from sebba_code.nodes.dispatch import (
    get_ready_tasks,
    is_dag_complete,
    is_dag_deadlocked,
)
from sebba_code.state import Task


def _task(id: str, status: str = "pending", depends_on: list[str] | None = None) -> Task:
    return Task(
        id=id,
        description=f"Task {id}",
        status=status,
        depends_on=depends_on or [],
        blocked_reason="",
        result_summary="",
        files_touched=[],
        target_files=[],
    )


class TestGetReadyTasks:
    def test_no_deps_are_ready(self):
        tasks = {"a": _task("a"), "b": _task("b")}
        ready = get_ready_tasks(tasks)
        assert len(ready) == 2

    def test_dep_not_done_blocks(self):
        tasks = {
            "a": _task("a"),
            "b": _task("b", depends_on=["a"]),
        }
        ready = get_ready_tasks(tasks)
        assert len(ready) == 1
        assert ready[0]["id"] == "a"

    def test_dep_done_unblocks(self):
        tasks = {
            "a": _task("a", status="done"),
            "b": _task("b", depends_on=["a"]),
        }
        ready = get_ready_tasks(tasks)
        assert len(ready) == 1
        assert ready[0]["id"] == "b"

    def test_multiple_deps_all_must_be_done(self):
        tasks = {
            "a": _task("a", status="done"),
            "b": _task("b"),
            "c": _task("c", depends_on=["a", "b"]),
        }
        ready = get_ready_tasks(tasks)
        ids = {t["id"] for t in ready}
        assert "c" not in ids
        assert "b" in ids

    def test_running_tasks_not_ready(self):
        tasks = {"a": _task("a", status="running")}
        ready = get_ready_tasks(tasks)
        assert len(ready) == 0

    def test_done_tasks_not_ready(self):
        tasks = {"a": _task("a", status="done")}
        ready = get_ready_tasks(tasks)
        assert len(ready) == 0


class TestDagComplete:
    def test_all_done(self):
        tasks = {
            "a": _task("a", status="done"),
            "b": _task("b", status="done"),
        }
        assert is_dag_complete(tasks) is True

    def test_not_all_done(self):
        tasks = {
            "a": _task("a", status="done"),
            "b": _task("b", status="pending"),
        }
        assert is_dag_complete(tasks) is False

    def test_empty_dag(self):
        assert is_dag_complete({}) is True


class TestDagDeadlock:
    def test_circular_dependency(self):
        tasks = {
            "a": _task("a", depends_on=["b"]),
            "b": _task("b", depends_on=["a"]),
        }
        assert is_dag_deadlocked(tasks) is True

    def test_no_deadlock_with_ready_tasks(self):
        tasks = {
            "a": _task("a"),
            "b": _task("b", depends_on=["a"]),
        }
        assert is_dag_deadlocked(tasks) is False

    def test_no_deadlock_when_complete(self):
        tasks = {
            "a": _task("a", status="done"),
            "b": _task("b", status="done"),
        }
        assert is_dag_deadlocked(tasks) is False

    def test_no_deadlock_with_running(self):
        tasks = {
            "a": _task("a", status="running"),
            "b": _task("b", depends_on=["a"]),
        }
        assert is_dag_deadlocked(tasks) is False
