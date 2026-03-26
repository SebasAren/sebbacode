"""Task dispatch and result collection for parallel DAG execution."""

import logging
import uuid
from typing import Literal

from langgraph.types import Command, Send

from sebba_code.state import AgentState, Task, TaskResult

logger = logging.getLogger("sebba_code")


def get_ready_tasks(tasks: dict[str, Task]) -> list[Task]:
    """Return tasks whose dependencies are all done."""
    done_ids = {tid for tid, t in tasks.items() if t["status"] == "done"}
    return [
        t for t in tasks.values()
        if t["status"] == "pending"
        and all(dep in done_ids for dep in t["depends_on"])
    ]


def is_dag_complete(tasks: dict[str, Task]) -> bool:
    """Check if all tasks are done."""
    return all(t["status"] == "done" for t in tasks.values())


def is_dag_deadlocked(tasks: dict[str, Task]) -> bool:
    """Check if no tasks are ready but some are not done (deadlock)."""
    if is_dag_complete(tasks):
        return False
    ready = get_ready_tasks(tasks)
    running = [t for t in tasks.values() if t["status"] == "running"]
    return len(ready) == 0 and len(running) == 0


def dispatch_tasks(state: AgentState) -> Command[Literal["task_worker", "extract_session"]]:
    """Fan out ready tasks to parallel workers via Send()."""
    tasks = dict(state["tasks"])  # copy for mutation

    if is_dag_complete(tasks):
        logger.info("All tasks complete, moving to extraction")
        return Command(goto="extract_session")

    if is_dag_deadlocked(tasks):
        logger.warning("DAG deadlocked — no tasks ready but %d remain",
                       sum(1 for t in tasks.values() if t["status"] != "done"))
        return Command(goto="extract_session")

    ready = get_ready_tasks(tasks)
    if not ready:
        # Tasks still running, wait — this shouldn't happen in practice
        # since collect_results routes back here only after workers finish
        logger.info("No tasks ready (some still running)")
        return Command(goto="extract_session")

    logger.info("Dispatching %d tasks: %s", len(ready), [t["id"] for t in ready])

    # Mark dispatched tasks as running
    for task in ready:
        tasks[task["id"]]["status"] = "running"

    sends = []
    for task in ready:
        worker_state = {
            "task": task,
            "messages": [],
            "worker_briefing": "",
            "memory": state["memory"],
            "target_files": task["target_files"],
            "working_branch": state.get("working_branch"),
        }
        sends.append(Send("task_worker", worker_state))

    return Command(goto=sends, update={"tasks": tasks})


def collect_results(state: AgentState) -> Command[Literal["dispatch_tasks", "extract_session"]]:
    """Collect worker results, update DAG, apply mutations, route next."""
    tasks = dict(state["tasks"])  # copy for mutation
    results = state.get("task_results", [])
    completed_ids = []

    for result in results:
        tid = result["task_id"]
        if tid in tasks and tasks[tid]["status"] != "done":
            tasks[tid]["status"] = "done"
            tasks[tid]["result_summary"] = result["summary"]
            if result.get("files_touched"):
                tasks[tid]["files_touched"] = result["files_touched"].split(", ") if isinstance(result["files_touched"], str) else result["files_touched"]
            completed_ids.append(tid)

    # Apply DAG mutations from workers (only for newly completed tasks)
    completed_set = set(completed_ids)
    for result in results:
        if result["task_id"] not in completed_set:
            continue
        for mutation in result.get("dag_mutations", []):
            if mutation["type"] == "add_blocking_task":
                new_id = mutation.get("new_task_id", f"task-{uuid.uuid4().hex[:6]}")
                tasks[new_id] = Task(
                    id=new_id,
                    description=mutation["description"],
                    status="pending",
                    depends_on=[],
                    blocked_reason="",
                    result_summary="",
                    files_touched=[],
                    target_files=mutation.get("target_files", []),
                )
                # The task that discovered this is blocked by the new task
                blocked_id = mutation.get("blocked_task_id")
                if blocked_id and blocked_id in tasks:
                    tasks[blocked_id]["depends_on"].append(new_id)
                    tasks[blocked_id]["status"] = "pending"
                    tasks[blocked_id]["blocked_reason"] = mutation.get("reason", "")
                logger.info("Added blocking task %s for %s", new_id, blocked_id)

            elif mutation["type"] == "add_subtask":
                new_id = mutation.get("new_task_id", f"task-{uuid.uuid4().hex[:6]}")
                tasks[new_id] = Task(
                    id=new_id,
                    description=mutation["description"],
                    status="pending",
                    depends_on=mutation.get("depends_on", []),
                    blocked_reason="",
                    result_summary="",
                    files_touched=[],
                    target_files=mutation.get("target_files", []),
                )
                logger.info("Added subtask %s", new_id)

    logger.info("Collected results for %d tasks", len(completed_ids))

    # Check if more work to do
    if is_dag_complete(tasks) or is_dag_deadlocked(tasks):
        return Command(
            goto="extract_session",
            update={
                "tasks": tasks,
                "task_results": [],  # clear for next wave
                "tasks_completed_this_session": completed_ids,
            },
        )

    return Command(
        goto="dispatch_tasks",
        update={
            "tasks": tasks,
            "task_results": [],  # clear for next wave
            "tasks_completed_this_session": completed_ids,
        },
    )
