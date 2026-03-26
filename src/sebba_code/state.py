"""Defines the TypedDict state schema for the agent graph."""

from typing import Annotated, Optional, TypedDict

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages


class AgentMemoryContext(TypedDict):
    """Assembled memory for this invocation."""

    l0_index: str
    l1_files: dict[str, str]
    l2_files: dict[str, str]
    active_rules: dict[str, str]
    session_history: str


class TodoItem(TypedDict):
    """A single todo parsed from the roadmap."""

    text: str
    done: bool
    index: int


class TodoSummary(TypedDict):
    """Summary of a completed todo, stored in state instead of commit files."""

    todo_text: str
    summary: str
    what_i_did: str
    decisions_made: str
    files_touched: str


class PlanState(TypedDict):
    """State for the planning-only graph."""

    # Planning loop
    user_request: str
    draft_roadmap: str
    planning_messages: Annotated[list[BaseMessage], add_messages]
    planning_iteration: int
    planning_complete: bool

    # Context (optional, enriches planning prompts)
    roadmap: str
    target_files: list[str]
    briefing: str
    memory: AgentMemoryContext


class AgentState(TypedDict):
    """Main graph state."""

    messages: Annotated[list[BaseMessage], add_messages]

    # Roadmap-driven
    roadmap: str
    current_todo: Optional[TodoItem]
    target_files: list[str]

    # Explorer output
    briefing: str
    exploration_mode: str

    # Memory
    memory: AgentMemoryContext

    # Git
    working_branch: Optional[str]

    # Session tracking
    todos_completed_this_session: list[str]
    todo_summaries: list[TodoSummary]

    # Configurable limits
    max_todos: Optional[int]  # None = use default from constants

    # Planning loop
    user_request: str
    draft_roadmap: str
    planning_messages: Annotated[list[BaseMessage], add_messages]
    planning_iteration: int
    planning_complete: bool
