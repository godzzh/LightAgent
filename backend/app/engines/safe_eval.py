"""受限表达式求值器（供 Code 节点使用）。

不使用 eval/exec，仅解释白名单 AST 节点，可安全处理变量、下标、比较、算术与少量内置函数。
"""
from __future__ import annotations

import json
import operator
from typing import Any

from app.core.exceptions import ValidationFailedError

_BINOPS = {
    "Add": operator.add,
    "Sub": operator.sub,
    "Mult": operator.mul,
    "Div": operator.truediv,
    "FloorDiv": operator.floordiv,
    "Mod": operator.mod,
    "Pow": operator.pow,
}
_CMPOPS = {
    "Eq": operator.eq,
    "NotEq": operator.ne,
    "Gt": operator.gt,
    "GtE": operator.ge,
    "Lt": operator.lt,
    "LtE": operator.le,
    "In": lambda a, b: a in b,
    "NotIn": lambda a, b: a not in b,
}


def _funcs() -> dict[str, Any]:
    return {
        "len": len,
        "str": str,
        "int": int,
        "float": float,
        "bool": bool,
        "abs": abs,
        "round": round,
        "min": min,
        "max": max,
        "sum": sum,
        "sorted": sorted,
        "json_dumps": lambda v: json.dumps(v, ensure_ascii=False, default=str),
        "json_loads": json.loads,
        "upper": lambda s: str(s).upper(),
        "lower": lambda s: str(s).lower(),
        "contains": lambda s, sub: sub in s,
        "split": lambda s, sep=None: str(s).split(sep),
        "join": lambda items, sep: sep.join(str(i) for i in items),
        "int_or": lambda v, d=0: int(v) if str(v).strip().lstrip("-").isdigit() else d,
    }


def safe_eval(expression: str, variables: dict[str, Any]) -> Any:
    import ast

    if not expression or not expression.strip():
        return None
    try:
        tree = ast.parse(expression.strip(), mode="eval")
    except SyntaxError as exc:
        raise ValidationFailedError(f"表达式语法错误: {exc.msg}") from exc

    funcs = _funcs()

    def walk(node: ast.AST) -> Any:
        if isinstance(node, ast.Expression):
            return walk(node.body)
        if isinstance(node, ast.Constant):
            return node.value
        if isinstance(node, ast.Name):
            if node.id in variables:
                return variables[node.id]
            if node.id in funcs:
                return funcs[node.id]
            if node.id in ("True", "False", "None"):
                return {"True": True, "False": False, "None": None}[node.id]
            raise ValidationFailedError(f"未定义变量: {node.id}")
        if isinstance(node, ast.BinOp):
            op = _BINOPS.get(type(node.op).__name__)
            if not op:
                raise ValidationFailedError(f"不支持的运算符: {type(node.op).__name__}")
            return op(walk(node.left), walk(node.right))
        if isinstance(node, ast.UnaryOp):
            val = walk(node.operand)
            if isinstance(node.op, ast.Not):
                return not val
            if isinstance(node.op, ast.USub):
                return -val
            return +val
        if isinstance(node, ast.BoolOp):
            vals = [walk(v) for v in node.values]
            return all(vals) if isinstance(node.op, ast.And) else any(vals)
        if isinstance(node, ast.Compare):
            left = walk(node.left)
            for op, comp in zip(node.ops, node.comparators):
                fn = _CMPOPS.get(type(op).__name__)
                if not fn:
                    raise ValidationFailedError(f"不支持的比较: {type(op).__name__}")
                right = walk(comp)
                if not fn(left, right):
                    return False
                left = right
            return True
        if isinstance(node, ast.Subscript):
            target = walk(node.value)
            key = walk(node.slice)
            try:
                return target[key]
            except (KeyError, IndexError, TypeError):
                raise ValidationFailedError(f"下标访问失败: {key}") from None
        if isinstance(node, ast.IfExp):
            return walk(node.body) if walk(node.test) else walk(node.orelse)
        if isinstance(node, ast.Call):
            if not isinstance(node.func, ast.Name):
                raise ValidationFailedError("仅支持调用白名单内置函数")
            fn = funcs.get(node.func.id)
            if not fn:
                raise ValidationFailedError(f"不允许的函数: {node.func.id}")
            return fn(*[walk(a) for a in node.args], **{k.arg: walk(k.value) for k in node.keywords if k.arg})
        if isinstance(node, ast.List):
            return [walk(e) for e in node.elts]
        if isinstance(node, ast.Tuple):
            return tuple(walk(e) for e in node.elts)
        if isinstance(node, ast.Dict):
            return {walk(k): walk(v) for k, v in zip(node.keys, node.values)}
        if isinstance(node, ast.JoinedStr):
            raise ValidationFailedError("Code 节点不支持 f-string，请使用 join/concat")
        raise ValidationFailedError(f"不支持的表达式元素: {type(node).__name__}")

    return walk(tree)
