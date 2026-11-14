"""测试环境：使用独立的临时 SQLite 数据库，避免污染开发数据。"""
from __future__ import annotations

import os
import tempfile

os.environ.setdefault("DATABASE_URL", f"sqlite+aiosqlite:///{tempfile.gettempdir()}/lightagent_test.db")
os.environ.setdefault("SECRET_KEY", "test-secret-key-for-pytest-only")

import pytest  # noqa: E402


@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"
