"""Implements the todo execution subgraph with LLM tool-calling loop."""

import logging

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langgraph.graph import END, StateGraph
from langgraph.prebuilt import ToolNode, tools_condition

from sebba_code.constants import DEBUG_PROMPTS
from sebba_code.llm import get_llm
from sebba_code.prompts import build_system_prompt
from sebba_code.state import AgentState
from sebba_code.tools import get_all_tools

logger = logging.getLogger("sebba_code")
debug_logger = logging.getLogger("sebba_code.debug")


def _summarise_message(msg) -> str:
    """One-line summary of a message for debug output."""
    if isinstance(msg, SystemMessage):
        return f"  system: ({len(msg.content)} chars)"
    if isinstance(msg, HumanMessage):
        preview = msg.content[:120].replace("\n", " ")
        return f"  human: {preview}..."
    if isinstance(msg, ToolMessage):
        preview = str(msg.content)[:100].replace("\n", " ")
        return f"  tool({msg.name}): {preview}"
    if isinstance(msg, AIMessage):
        if msg.tool_calls:
            calls = ", ".join(tc["name"] for tc in msg.tool_calls)
            return f"  ai: [calls: {calls}]"
        preview = (msg.content or "")[:120].replace("\n", " ")
        return f"  ai: {preview}"
    return f"  {msg.__class__.__name__}: ({len(str(msg.content))} chars)"


def _llm_call(state: AgentState) -> dict:
    """Invoke the LLM with the assembled system prompt and all tools bound."""
    logger.info("execute: calling LLM (%d messages in state)", len(state["messages"]))
    tools = get_all_tools()
    llm = get_llm().bind_tools(tools)

    system_prompt = build_system_prompt(state)
    messages = [SystemMessage(content=system_prompt)] + list(state["messages"])

    # OpenAI-compatible APIs require at least one user message
    injected_human_msg = None
    if not any(isinstance(m, HumanMessage) for m in messages):
        todo = state.get("current_todo", {})
        task_text = todo.get("text", "Proceed with the current task.")
        briefing = state.get("briefing", "")
        user_msg = f"Execute this todo: {task_text}"
        if briefing:
            user_msg += f"\n\nBriefing:\n{briefing}"
        injected_human_msg = HumanMessage(content=user_msg)
        messages.append(injected_human_msg)

    if DEBUG_PROMPTS:
        debug_logger.debug("── system prompt (%d chars) ──\n%s", len(system_prompt), system_prompt[:2000])
        debug_logger.debug("── messages (%d) ──", len(messages))
        for msg in messages:
            debug_logger.debug(_summarise_message(msg))

    response = llm.invoke(messages)

    if DEBUG_PROMPTS:
        debug_logger.debug("── response ──\n%s", _summarise_message(response))

    if injected_human_msg:
        return {"messages": [injected_human_msg, response]}
    return {"messages": [response]}


def build_execute_subgraph():
    """Build the inner agent loop: LLM call → tool execution → repeat."""
    tools = get_all_tools()

    graph = StateGraph(AgentState)
    graph.add_node("llm_call", _llm_call)
    graph.add_node("tools", ToolNode(tools))

    graph.set_entry_point("llm_call")
    graph.add_conditional_edges("llm_call", tools_condition)
    graph.add_edge("tools", "llm_call")

    return graph.compile()
