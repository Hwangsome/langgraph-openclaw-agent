from __future__ import annotations

import functools
import os
import re
import sys
from typing import Annotated, List, Optional

from dotenv import load_dotenv
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, ToolMessage
from langchain_core.tools import tool
from langgraph.graph import END, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode

from .tools import calculator as _calculator
from .tools import read_file as _read_file

# Load env exactly once on import (graph module is imported by the CLI entry).
load_dotenv(override=False)


@tool("calculator")
def calculator(expression: str) -> str:
    """Safely evaluate a basic arithmetic expression."""
    return _calculator(expression)


@tool("read_file")
def read_file(path: str) -> str:
    """Read a UTF-8 text file from a restricted allowed root and size limit."""
    return _read_file(path)


class FakeReActLLM:
    """A tiny rule-based LLM that produces tool calls (for demos).

    It emits exactly one tool call if it can detect a calculator request or read_file request.
    Then, after receiving ToolMessage(s), it emits a final answer.
    """

    def invoke(self, messages: List[BaseMessage]) -> AIMessage:
        last = messages[-1]

        # If we just got a tool result, finalize.
        if isinstance(last, ToolMessage):
            return AIMessage(content=f"Result: {last.content}")

        # Find the last human query
        human = next((m for m in reversed(messages) if isinstance(m, HumanMessage)), None)
        text = human.content if human else ""

        # Simple patterns
        m_calc = re.search(r"(?:calc|calculate|calculator|算|计算)\s*[:：]?\s*(.+)$", text, re.I)
        if m_calc:
            expr = m_calc.group(1).strip()
            return AIMessage(
                content="I'll use calculator.",
                tool_calls=[{"name": "calculator", "args": {"expression": expr}, "id": "call_calc"}],
            )

        m_read = re.search(r"(?:read|cat|打开|读取)\s*[:：]?\s*(.+)$", text, re.I)
        if m_read:
            path = m_read.group(1).strip().strip('"')
            return AIMessage(
                content="I'll use read_file.",
                tool_calls=[{"name": "read_file", "args": {"path": path}, "id": "call_read"}],
            )

        # Default: still demonstrate a tool call by doing a trivial calc
        return AIMessage(
            content="I'll do a quick check with calculator.",
            tool_calls=[{"name": "calculator", "args": {"expression": "1+1"}, "id": "call_default"}],
        )


@functools.lru_cache(maxsize=1)
def _get_llm():
    """Return a callable LLM-like object with .invoke(messages)->AIMessage.

    Cached so each ReAct turn doesn't reconstruct the LLM/tool bindings.
    """
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return FakeReActLLM()

    # Real model
    from langchain_openai import ChatOpenAI

    model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    base_url = os.getenv("OPENAI_BASE_URL")

    kwargs = {"model": model, "temperature": 0}
    if base_url:
        kwargs["base_url"] = base_url

    return ChatOpenAI(**kwargs).bind_tools([calculator, read_file])


class AgentState(dict):
    messages: Annotated[list, add_messages]


def _llm_node(state: AgentState) -> dict:
    llm = _get_llm()
    msg = llm.invoke(state["messages"])

    # stderr log for visibility
    if getattr(msg, "tool_calls", None):
        print(f"[oc-lg-agent] tool_calls: {msg.tool_calls}", file=sys.stderr)

    return {"messages": [msg]}


def _should_continue(state: AgentState) -> str:
    last = state["messages"][-1]
    if isinstance(last, AIMessage) and getattr(last, "tool_calls", None):
        return "tools"
    return "final"


def build_graph():
    tools_node = ToolNode([calculator, read_file])

    g = StateGraph(AgentState)
    g.add_node("llm", _llm_node)
    g.add_node("tools", tools_node)

    g.set_entry_point("llm")
    g.add_conditional_edges("llm", _should_continue, {"tools": "tools", "final": END})
    g.add_edge("tools", "llm")

    return g.compile()


graph = build_graph()
