"""Defines the TypedDict state schema for the agent graph."""

import operator
from typing import Annotated, Literal, Optional, TypedDict

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages


class AgentMemoryContext(TypedDict):
    """Assembled memory for this invocation."""

    l0_index: str
    l1_files: dict[str, str]
    l2_files: dict[str, str]
    active_rules: dict[str, str]
    session_history: str


class Task(TypedDict):
    """A single task in the execution DAG."""

    id: str
    description: str
    status: Literal["pending", "running", "done", "blocked"]
    depends_on: list[str]  # task IDs this depends on
    blocked_reason: str
    result_summary: str
    files_touched: list[str]
    target_files: list[str]


class TaskResult(TypedDict):
    """Result produced by a task worker."""

    task_id: str
    summary: str
    what_i_did: str
    decisions_made: str
    files_touched: str
    dag_mutations: list[dict]  # new tasks / blocks discovered
    memory_updates: dict  # collected for sequential application


class WorkerState(TypedDict):
    """Per-task state passed via Send()."""

    task: Task
    messages: Annotated[list[BaseMessage], add_messages]
    briefing: str
    memory: AgentMemoryContext
    target_files: list[str]
    working_branch: Optional[str]
    task_result: Optional[TaskResult]


class AgentState(TypedDict):
    """Unified graph state for planning + execution."""

    messages: Annotated[list[BaseMessage], add_messages]

    # Planning
    user_request: str
    draft_plan: str
    planning_messages: Annotated[list[BaseMessage], add_messages]
    planning_iteration: int
    planning_complete: bool
    rejection_reason: str

    # Task DAG (replaces roadmap)
    tasks: dict[str, Task]
    task_results: Annotated[list[TaskResult], operator.add]

    # Context
    memory: AgentMemoryContext
    working_branch: Optional[str]
    briefing: str

    # Session tracking
    tasks_completed_this_session: Annotated[list[str], operator.add]

    # Human-in-the-loop
    plan_approved: Optional[bool]
