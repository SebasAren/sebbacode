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

    # Git/GCC
    working_branch: Optional[str]
    session_start_commit: int

    # Session tracking
    todos_completed_this_session: list[str]
