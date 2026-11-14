"""API 集成测试：登录、健康检查、应用 CRUD、统一响应结构。"""
from __future__ import annotations

import os
import tempfile

import pytest
from fastapi.testclient import TestClient

os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{tempfile.gettempdir()}/lightagent_api_test.db"

from app.main import app  # noqa: E402


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="module")
def token(client):
    res = client.post("/api/v1/auth/login", json={"account": "admin", "password": "admin123"})
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["code"] == 0
    return body["data"]["access_token"]


def auth(token):
    return {"Authorization": f"Bearer {token}"}


def test_health(client):
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json()["status"] == "ok"


def test_login_wrong_password(client):
    res = client.post("/api/v1/auth/login", json={"account": "admin", "password": "bad"})
    assert res.status_code == 401
    assert res.json()["code"] == 40100


def test_requires_auth(client):
    res = client.get("/api/v1/applications")
    assert res.status_code == 401


def test_application_crud(client, token):
    created = client.post(
        "/api/v1/applications",
        json={"name": "接口测试应用", "app_type": "chat_agent", "template": "blank"},
        headers=auth(token),
    )
    assert created.status_code == 200, created.text
    app_id = created.json()["data"]["id"]

    listed = client.get("/api/v1/applications", headers=auth(token))
    assert listed.status_code == 200
    assert listed.json()["data"]["total"] >= 1

    updated = client.patch(
        f"/api/v1/applications/{app_id}",
        json={"description": "已更新"},
        headers=auth(token),
    )
    assert updated.json()["data"]["description"] == "已更新"

    deleted = client.delete(f"/api/v1/applications/{app_id}", headers=auth(token))
    assert deleted.json()["data"]["ok"] is True


def test_workflow_create_and_validate(client, token):
    wf = client.post("/api/v1/workflows", json={"name": "接口测试流程"}, headers=auth(token))
    assert wf.status_code == 200
    wf_id = wf.json()["data"]["id"]

    check = client.post(f"/api/v1/workflows/{wf_id}/validate", headers=auth(token))
    assert check.json()["data"]["ok"] is True


def test_knowledge_retrieve_without_embedding_returns_fallback(client, token):
    ds = client.post(
        "/api/v1/knowledge/datasets",
        json={"name": "接口测试知识库", "chunk_size": 200, "chunk_overlap": 20},
        headers=auth(token),
    )
    assert ds.status_code == 200
    ds_id = ds.json()["data"]["id"]
    res = client.post(
        "/api/v1/knowledge/retrieve",
        json={"query": "测试", "dataset_ids": [ds_id], "top_k": 3, "threshold": 0.1},
        headers=auth(token),
    )
    assert res.status_code == 200
    assert "results" in res.json()["data"]


def test_dashboard_endpoints_return_data(client, token):
    """回归测试：select(Model.id).scalars() 返回主键值本身，接口不能再取 .id。"""
    for ep in ("overview", "recent", "trend"):
        res = client.get(f"/api/v1/dashboard/{ep}", headers=auth(token))
        assert res.status_code == 200, f"{ep}: {res.text}"

    overview = client.get("/api/v1/dashboard/overview", headers=auth(token)).json()["data"]
    assert {"applications", "published", "datasets", "workflows", "runs", "tokens"} <= set(overview["stats"])

    trend = client.get("/api/v1/dashboard/trend", headers=auth(token)).json()["data"]
    assert len(trend["trend"]) == 7
    assert all("date" in p and "count" in p for p in trend["trend"])


def test_logs_runs_all_types(client, token):
    """回归测试：日志列表三种类型都必须可用（Agent 分支曾误取主键 .id 导致 500）。"""
    for run_type in ("agent", "workflow", "llm"):
        res = client.get(
            f"/api/v1/logs/runs?run_type={run_type}&page=1&page_size=20&keyword=&days=7",
            headers=auth(token),
        )
        assert res.status_code == 200, f"{run_type}: {res.text}"
        data = res.json()["data"]
        assert {"items", "total", "page", "page_size"} <= set(data)

    # 带应用过滤与状态过滤也不能报错
    res = client.get(
        "/api/v1/logs/runs?run_type=workflow&page=1&page_size=20&status=succeeded&days=30",
        headers=auth(token),
    )
    assert res.status_code == 200, res.text


def test_logs_stats(client, token):
    res = client.get("/api/v1/logs/stats?days=7", headers=auth(token))
    assert res.status_code == 200, res.text
    assert {"calls", "failed", "prompt_tokens", "completion_tokens", "avg_latency_ms"} <= set(
        res.json()["data"]
    )
