"""工具层测试：安全计算、参数校验、SSRF 防护。"""
import pytest

from app.core.exceptions import ValidationFailedError
from app.tool_registry.builtin import ensure_builtin_registered
from app.tool_registry.registry import registry
from app.utils.net import validate_public_url


@pytest.fixture(scope="module", autouse=True)
def _register():
    ensure_builtin_registered()


async def test_math_calc_result():
    result = await registry.execute_tool("math_calc", {"expression": "(12+8)*3/4"})
    assert result["result"] == 15


async def test_math_calc_blocks_code_execution():
    with pytest.raises(Exception):
        await registry.execute_tool("math_calc", {"expression": "__import__('os').system('echo hi')"})


async def test_math_calc_missing_param():
    with pytest.raises(ValidationFailedError):
        await registry.execute_tool("math_calc", {})


async def test_json_query_path():
    result = await registry.execute_tool("json_query", {"json_text": '{"a":{"b":[1,2,3]}}', "path": "a.b.1"})
    assert result == 2


async def test_text_process_stats():
    result = await registry.execute_tool("text_process", {"text": "hello 世界", "operation": "stats"})
    assert result["cjk_chars"] == 2


async def test_current_time_returns_iso():
    result = await registry.execute_tool("current_time", {"timezone": "UTC"})
    assert "iso" in result and "weekday" in result


def test_ssrf_blocks_localhost():
    with pytest.raises(ValidationFailedError):
        validate_public_url("http://127.0.0.1:8000/admin")


def test_ssrf_blocks_metadata_ip():
    with pytest.raises(ValidationFailedError):
        validate_public_url("http://169.254.169.254/latest/meta-data/")


def test_ssrf_blocks_non_http_scheme():
    with pytest.raises(ValidationFailedError):
        validate_public_url("file:///etc/passwd")
