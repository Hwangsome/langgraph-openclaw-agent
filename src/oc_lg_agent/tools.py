from __future__ import annotations

import ast
import operator as op
import os
from dataclasses import dataclass
from pathlib import Path


# ---- calculator (safe) ----

_ALLOWED_BINOPS: dict[type, object] = {
    ast.Add: op.add,
    ast.Sub: op.sub,
    ast.Mult: op.mul,
    ast.Div: op.truediv,
    ast.FloorDiv: op.floordiv,
    ast.Mod: op.mod,
    ast.Pow: op.pow,
}
_ALLOWED_UNARYOPS: dict[type, object] = {
    ast.UAdd: op.pos,
    ast.USub: op.neg,
}


def _eval_expr(node: ast.AST) -> float:
    if isinstance(node, ast.Expression):
        return _eval_expr(node.body)

    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return float(node.value)

    if isinstance(node, ast.BinOp) and type(node.op) in _ALLOWED_BINOPS:
        left = _eval_expr(node.left)
        right = _eval_expr(node.right)
        return float(_ALLOWED_BINOPS[type(node.op)](left, right))

    if isinstance(node, ast.UnaryOp) and type(node.op) in _ALLOWED_UNARYOPS:
        operand = _eval_expr(node.operand)
        return float(_ALLOWED_UNARYOPS[type(node.op)](operand))

    raise ValueError("Unsupported expression")


def calculator(expression: str) -> str:
    """Safely evaluate a basic arithmetic expression.

    Supported: numbers, + - * / // % **, parentheses, unary +/-.
    """
    expr = expression.strip()
    if not expr:
        raise ValueError("Empty expression")

    tree = ast.parse(expr, mode="eval")
    result = _eval_expr(tree)
    # Render ints without .0
    if abs(result - int(result)) < 1e-12:
        return str(int(result))
    return str(result)


# ---- read_file (restricted) ----

@dataclass(frozen=True)
class ReadFileConfig:
    allowed_root: Path
    max_bytes: int


def _get_read_file_config() -> ReadFileConfig:
    root = os.getenv("OC_LG_AGENT_ALLOWED_ROOT", ".")
    max_bytes = int(os.getenv("OC_LG_AGENT_MAX_BYTES", "65536"))
    return ReadFileConfig(allowed_root=Path(root).resolve(), max_bytes=max_bytes)


def read_file(path: str) -> str:
    """Read a text file with strict path + size limits."""
    cfg = _get_read_file_config()

    p = Path(path).expanduser()
    if not p.is_absolute():
        # resolve relative paths against allowed_root
        p = (cfg.allowed_root / p).resolve()
    else:
        p = p.resolve()

    # Ensure within allowed root
    try:
        p.relative_to(cfg.allowed_root)
    except Exception as e:
        raise PermissionError(f"Path not allowed. allowed_root={cfg.allowed_root}") from e

    if not p.exists() or not p.is_file():
        raise FileNotFoundError(str(p))

    size = p.stat().st_size
    if size > cfg.max_bytes:
        raise ValueError(f"File too large: {size} bytes (max {cfg.max_bytes})")

    data = p.read_text(encoding="utf-8", errors="replace")
    return data
