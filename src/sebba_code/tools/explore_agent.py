"""Explore subagent tool — LLM-guided codebase exploration for workers."""

import logging

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.tools import tool
from langgraph.prebuilt import ToolNode

from sebba_code.tools.code import read_file
from sebba_code.tools.search import search_code, search_files

logger = logging.getLogger("sebba_code")

_EXPLORE_SYSTEM = """You are exploring a codebase to answer a question. Use the search tools to find relevant files and code, then read them to build understanding.

Be thorough but efficient:
- Start with broad searches (search_files, search_code) to locate relevant areas
- Read key files to understand patterns and structure
- Synthesize your findings into a clear, actionable answer

Your final message (without tool calls) will be returned as the answer."""

_INNER_TOOLS = [search_files, search_code, read_file]
_TOOL_NODE = ToolNode(_INNER_TOOLS)

MAX_ITERATIONS = 5


@tool
def explore_codebase(question: str) -> str:
    """Explore the codebase to answer a question. Uses LLM-guided search
    to find relevant files, read them, and synthesize an answer.

    Use this when you need to understand how something works, find where
    code lives, or discover patterns before making changes.

    Args:
        question: What you want to understand about the codebase
    """
    from sebba_code.llm import get_cheap_llm, invoke_with_timeout

    llm = get_cheap_llm().bind_tools(_INNER_TOOLS)

    messages = [
        SystemMessage(content=_EXPLORE_SYSTEM),
        HumanMessage(content=question),
    ]

    for i in range(MAX_ITERATIONS):
        try:
            response = invoke_with_timeout(llm, messages, timeout_seconds=30)
        except TimeoutError:
            logger.warning("explore_codebase: LLM call %d timed out", i)
            break
        except Exception as e:
            logger.warning("explore_codebase: LLM call %d failed: %s", i, e)
            break

        messages.append(response)

        if not getattr(response, "tool_calls", None):
            return response.content or "No findings."

        # Execute tool calls
        tool_state = {"messages": messages}
        tool_result = _TOOL_NODE.invoke(tool_state)
        tool_messages = tool_result["messages"]
        messages.extend(tool_messages)

    # If we exhausted iterations, get a final answer
    last_ai = [m for m in reversed(messages) if isinstance(m, AIMessage) and m.content]
    if last_ai:
        return last_ai[0].content
    return "Exploration did not produce findings."
