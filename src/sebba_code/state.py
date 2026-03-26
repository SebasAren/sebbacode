"""Defines the TypedDict state schema for the agent graph."""

import operator
from typing import Annotated, Literal, Optional, TypedDict

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages


class L2EntryDict(TypedDict):
    """A serialisable L2 entry stored in graph state (passed to summariser)."""

    content: str
    file: str
    topic: str


class L1SummaryDict(TypedDict):
    """A serialised L1 summary produced by the summariser."""

    file: str
    topic: str
    summary: str
    source_l2_key: str
    l2_preview: str
    created_at: str
    version: int
    summary_model: str


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
    progress_summary: str  # what was done before blocking (for resume)


class TaskResult(TypedDict):
    """Result produced by a task worker."""

    task_id: str
    summary: str
    what_i_did: str
    decisions_made: str
    files_touched: str
    dag_mutations: list[dict]  # new tasks / blocks discovered
    memory_updates: dict  # collected for sequential application


class WorkerOutput(TypedDict):
    """Output schema for the worker subgraph — only task_results flows to parent."""

    task_results: Annotated[list[TaskResult], operator.add]


class WorkerState(TypedDict):
    """Per-task state passed via Send()."""

    task: Task
    messages: Annotated[list[BaseMessage], add_messages]
    worker_briefing: str
    predecessor_context: str  # summaries from dependency tasks + own prior progress
    memory: AgentMemoryContext
    target_files: list[str]
    working_branch: Optional[str]
    task_result: Optional[TaskResult]
    task_results: Annotated[list[TaskResult], operator.add]  # output to parent


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

    # L2 extraction output — consumed by summarize_to_l1
    l2_entries: list[L2EntryDict]

    # L1 summarisation output — written by summarize_to_l1
    l1_summaries: list[L1SummaryDict]

    # Human-in-the-loop
    plan_approved: Optional[bool]
