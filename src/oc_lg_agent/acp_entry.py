from __future__ import annotations

import sys
from typing import Optional

from langchain_core.messages import HumanMessage

from .graph import graph


def run_query(query: str) -> str:
    result = graph.invoke({"messages": [HumanMessage(content=query)]})
    # result["messages"] is the full transcript; last is final AI message
    final = result["messages"][-1]
    return getattr(final, "content", str(final))


def _read_stdin() -> str:
    data = sys.stdin.read()
    return data.strip("\n")


def main(argv: Optional[list[str]] = None) -> None:
    argv = list(sys.argv[1:] if argv is None else argv)

    if argv:
        query = " ".join(argv)
    else:
        query = _read_stdin()

    if not query.strip():
        print("Usage: python -m oc_lg_agent.acp_entry \"<query>\"  (or pipe via stdin)", file=sys.stderr)
        raise SystemExit(2)

    out = run_query(query)
    print(out)


if __name__ == "__main__":
    main()
