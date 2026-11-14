"""内置工具：安全数学计算（AST 白名单，不使用 eval 执行任意代码）。"""
from __future__ import annotations

import ast
import math
import operator
from typing import Any

from app.core.exceptions import ValidationFailedError
from app.tool_registry.registry import BaseTool, ToolSpec, register

_ALLOWED_OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
}
_ALLOWED_FUNCS = {
    "abs": abs,
    "round": round,
    "min": min,
    "max": max,
    "sum": sum,
    "sqrt": math.sqrt,
    "log": math.log,
    "log10": math.log10,
    "exp": math.exp,
    "sin": math.sin,
    "cos": math.cos,
    "tan": math.tan,
    "floor": math.floor,
    "ceil": math.ceil,
    "pow": pow,
}
_CONSTANTS = {"pi": math.pi, "e": math.e}


def _eval_node(node: ast.AST) -> Any:
    if isinstance(node, ast.Expression):
        return _eval_node(node.body)
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return node.value
    if isinstance(node, ast.BinOp) and type(node.op) in _ALLOWED_OPS:
        left, right = _eval_node(node.left), _eval_node(node.right)
        if isinstance(node.op, ast.Pow) and abs(right) > 100:
            raise ValidationFailedError("指数过大")
        return _ALLOWED_OPS[type(node.op)](left, right)
    if isinstance(node, ast.UnaryOp) and type(node.op) in _ALLOWED_OPS:
        return _ALLOWED_OPS[type(node.op)](_eval_node(node.operand))
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
        fn = _ALLOWED_FUNCS.get(node.func.id)
        if not fn:
            raise ValidationFailedError(f"不允许的函数: {node.func.id}")
        args = [_eval_node(a) for a in node.args]
        return fn(*args)
    if isinstance(node, ast.Name) and node.id in _CONSTANTS:
        return _CONSTANTS[node.id]
    if isinstance(node, ast.Tuple):
        return tuple(_eval_node(e) for e in node.elts)
    raise ValidationFailedError(f"不支持的表达式元素: {type(node).__name__}")


class MathCalcTool(BaseTool):
    spec = ToolSpec(
        name="math_calc",
        description="计算数学表达式，支持 + - * / // % ** 与 sqrt/log/sin/cos/round 等函数，例如 (12+8)*3/4。",
        parameters=[
            {"name": "expression", "type": "string", "description": "数学表达式", "required": True},
        ],
    )

    async def execute(self, args: dict) -> dict:
        expr = str(args["expression"]).strip()
        if len(expr) > 500:
            raise ValidationFailedError("表达式过长")
        try:
            tree = ast.parse(expr, mode="eval")
            value = _eval_node(tree)
        except SyntaxError as exc:
            raise ValidationFailedError(f"表达式语法错误: {expr}") from exc
        return {"expression": expr, "result": value}


register(MathCalcTool())
