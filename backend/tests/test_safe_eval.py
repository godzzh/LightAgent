"""受限表达式求值测试。"""
import pytest

from app.core.exceptions import ValidationFailedError
from app.engines.safe_eval import safe_eval


def test_arithmetic_and_vars():
    assert safe_eval("a + b * 2", {"a": 1, "b": 3}) == 7


def test_subscript_and_functions():
    assert safe_eval("len(items)", {"items": [1, 2, 3]}) == 3
    assert safe_eval("data['name']", {"data": {"name": "la"}}) == "la"


def test_comparison():
    assert safe_eval("score > 60 and score < 100", {"score": 88}) is True


def test_undefined_variable_raises():
    with pytest.raises(ValidationFailedError):
        safe_eval("missing + 1", {})


def test_blocks_dunder_access():
    with pytest.raises(ValidationFailedError):
        safe_eval("__import__('os')", {})
