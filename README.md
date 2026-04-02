# langgraph-openclaw-agent

Minimal LangChain + LangGraph (ReAct loop) agent with an OpenClaw ACP-callable entry.

## Features

- Python package (uv-friendly) via `pyproject.toml`
- LangGraph ReAct loop: **LLM node → tools node → LLM node** until final
- Tools:
  - `calculator`: safe arithmetic evaluator (AST whitelist)
  - `read_file`: restricted file reader (allowed root + size limit)
- **MOCK mode** (no `OPENAI_API_KEY`): uses a tiny rule-based LLM that still performs a real tool call
- Entrypoint:
  - `uv run python -m oc_lg_agent.acp_entry "<query>"` (recommended)
  - or stdin

## Setup (local)

### 1) Install deps

Using `uv`:

```bash
cd /Users/bill/.openclaw/workspace-coordinator/langgraph-openclaw-agent
uv venv
uv pip install -e .
```

### 2) Configure env

Copy `.env.example` to `.env` and edit as needed:

```bash
cp .env.example .env
```

- If `OPENAI_API_KEY` is empty/unset → MOCK mode
- Otherwise uses `langchain-openai` ChatOpenAI

## Run (smoke)

### MOCK mode (no key needed)

```bash
# Ensure OPENAI_API_KEY is NOT set
unset OPENAI_API_KEY

uv run python -m oc_lg_agent.acp_entry "calc: 2*(3+4)"
```

You should see a tool-call log on **stderr** like:

```
[oc-lg-agent] tool_calls: ...
```

And stdout prints the final answer.

### Real model mode

```bash
export OPENAI_API_KEY=YOUR_KEY
uv run python -m oc_lg_agent.acp_entry "calculate: 12/5"
```

## Tool: read_file safety

The `read_file` tool is restricted by:

- `OC_LG_AGENT_ALLOWED_ROOT` (default: `.`)
- `OC_LG_AGENT_MAX_BYTES` (default: `65536`)

Example:

```bash
export OC_LG_AGENT_ALLOWED_ROOT=.
uv run python -m oc_lg_agent.acp_entry "read: README.md"
```

## OpenClaw ACP integration (command form)

In an ACP pipeline, invoke this agent by running:

```bash
uv run python -m oc_lg_agent.acp_entry "<query>"
```

or via stdin:

```bash
echo "calc: 40+2" | uv run python -m oc_lg_agent.acp_entry
```

If you are not using `uv`, see **Appendix: Plain Python (non‑ClawX environments)** below.

## Appendix: Plain Python (non‑ClawX environments)

If you are running outside ClawX and you already have dependencies installed in an active Python environment, you can run the same module with plain Python:

```bash
python -m oc_lg_agent.acp_entry "calc: 2*(3+4)"
```

(For reproducibility, this repo’s primary instructions use `uv run python ...` and commit `uv.lock`.)
