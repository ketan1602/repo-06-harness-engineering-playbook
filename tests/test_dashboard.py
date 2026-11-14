"""Dashboard route tests — no external API calls made."""
from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from dashboard.app import app


@pytest.fixture
def client():
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


@pytest.mark.asyncio
async def test_overview_returns_200(client):
    async with client as c:
        resp = await c.get("/")
    assert resp.status_code == 200
    assert "Harness Engineering" in resp.text


@pytest.mark.asyncio
async def test_demo_get_returns_200(client):
    async with client as c:
        resp = await c.get("/demo")
    assert resp.status_code == 200
    assert "Breaking-Change" in resp.text


@pytest.mark.asyncio
async def test_metrics_returns_200(client):
    async with client as c:
        resp = await c.get("/metrics")
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_eval_get_returns_200(client):
    async with client as c:
        resp = await c.get("/eval")
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_api_overview_returns_article_06(client):
    async with client as c:
        resp = await c.get("/api/overview")
    assert resp.status_code == 200
    data = resp.json()
    assert data["article_number"] == "06"
    assert "Discipline" in data["article_title"]


@pytest.mark.asyncio
async def test_api_demo_examples_returns_v1_and_v2(client):
    async with client as c:
        resp = await c.get("/api/demo/examples")
    assert resp.status_code == 200
    data = resp.json()
    assert "v1" in data and "v2" in data
    assert "AgentHarness" in data["v1"]


@pytest.mark.asyncio
async def test_demo_post_no_breaking_changes(client):
    src = "class AgentHarness:\n    def run(self, input_data): pass"
    async with client as c:
        resp = await c.post("/demo", data={"v1_source": src, "v2_source": src})
    assert resp.status_code == 200
    data = resp.json()
    assert data["is_breaking"] is False
    assert data["breaking_change_count"] == 0


@pytest.mark.asyncio
async def test_demo_post_detects_breaking_change(client):
    v1 = '__all__ = ["AgentHarness", "HarnessConfig"]\nclass AgentHarness: pass\nclass HarnessConfig: pass'
    v2 = '__all__ = ["AgentHarness"]\nclass AgentHarness: pass'
    async with client as c:
        resp = await c.post("/demo", data={"v1_source": v1, "v2_source": v2})
    assert resp.status_code == 200
    data = resp.json()
    assert data["is_breaking"] is True
    assert data["breaking_change_count"] >= 1


@pytest.mark.asyncio
async def test_api_metrics_null_renders_not_measured(client, tmp_path, monkeypatch):
    (tmp_path / "measurements").mkdir()
    (tmp_path / "measurements" / "discipline_metrics.json").write_text(
        '{"detection_time_seconds": null, "upgrade_success_rate_pct": null, "contract_drift_pct": null}'
    )
    monkeypatch.chdir(tmp_path)
    async with client as c:
        resp = await c.get("/api/metrics")
    assert resp.status_code == 200
    charts = resp.json()["charts"]
    for key in ("detection_stat", "upgrade_bar", "drift_stat"):
        assert "not measured" in charts[key]
    assert ">0%<" not in charts["upgrade_bar"]
