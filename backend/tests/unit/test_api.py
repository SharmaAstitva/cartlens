"""Unit tests for the HTTP layer. Queries are faked; no database is needed."""

from contextlib import contextmanager
from datetime import date

import psycopg
import pytest
from fastapi.testclient import TestClient

from app import main
from app.ask import EXAMPLES, AskError, AskUnavailable
from app.config import load_settings


class FakePool:
    def __init__(self, fail=False):
        self.fail = fail

    @contextmanager
    def connection(self, timeout=None):
        if self.fail:
            raise psycopg.OperationalError("connection refused")
        yield object()


@pytest.fixture
def client():
    app = main.create_app(load_settings({"CORS_ORIGINS": "https://   cartlens-bice.vercel.app"}))
    app.state.pool = FakePool()
    return TestClient(app)


def test_root_points_to_docs(client):
    assert client.get("/").json()["docs"] == "/api/docs"


def test_health_ok(client, monkeypatch):
    monkeypatch.setattr(
        main.queries,
        "health_snapshot",
        lambda conn: {"counts": {"raw_events": 10}, "last_run": None, "data_through": None},
    )
    body = client.get("/api/health").json()
    assert body["status"] == "ok"
    assert body["database"] == "ok"
    assert body["counts"] == {"raw_events": 10}
    assert body["llm"] == {"mode": "demo", "model": None}


def test_health_degraded_when_db_down(client):
    client.app.state.pool = FakePool(fail=True)
    res = client.get("/api/health")
    assert res.status_code == 200
    assert res.json()["status"] == "degraded"
    assert "OperationalError" in res.json()["database"]


def test_llm_mode_reported_when_key_set():
    app = main.create_app(load_settings({"GROQ_API_KEY": "gsk_x"}))
    app.state.pool = FakePool(fail=True)
    assert TestClient(app).get("/api/health").json()["llm"] == {
        "mode": "groq",
        "model": "openai/gpt-oss-120b",
    }


@pytest.mark.parametrize(
    ("path", "func", "kwargs"),
    [
        ("/api/v1/kpis?days=30", "kpis", {"days": 30}),
        ("/api/v1/cities?limit=5", "cities", {"limit": 5}),
        ("/api/v1/funnel?months=3", "funnel", {"months": 3}),
        ("/api/v1/cohorts?months=6", "cohorts", {"months": 6}),
        ("/api/v1/segments", "segments", {}),
        ("/api/v1/pipeline/runs?limit=7", "pipeline_runs", {"limit": 7}),
    ],
)
def test_data_endpoints_pass_params_to_queries(client, monkeypatch, path, func, kwargs):
    seen = {}

    def fake(conn, **kw):
        seen.update(kw)
        return {"ok": True, "when": date(2026, 11, 3)}

    monkeypatch.setattr(main.queries, func, fake)
    res = client.get(path)
    assert res.status_code == 200
    assert res.json() == {"ok": True, "when": "2026-11-03"}
    assert seen == kwargs


@pytest.mark.parametrize(
    "path", ["/api/v1/kpis?days=3", "/api/v1/cities?limit=0", "/api/v1/cohorts?months=99"]
)
def test_out_of_range_params_are_rejected(client, path):
    assert client.get(path).status_code == 422


def test_missing_tables_explain_what_to_do(client, monkeypatch):
    def boom(conn, **kw):
        raise psycopg.errors.UndefinedTable('relation "analytics.fct_daily_kpis" does not exist')

    monkeypatch.setattr(main.queries, "segments", boom)
    res = client.get("/api/v1/segments")
    assert res.status_code == 503
    assert "pipeline" in res.json()["detail"]


def test_database_down_returns_503(client):
    client.app.state.pool = FakePool(fail=True)
    res = client.get("/api/v1/segments")
    assert res.status_code == 503
    assert res.json()["detail"] == "Database unavailable"


def test_examples_endpoint(client):
    body = client.get("/api/v1/ask/examples").json()
    assert body["mode"] == "demo"
    assert body["questions"] == [e["question"] for e in EXAMPLES]


def test_ask_success(client, monkeypatch):
    seen = {}

    def fake_ask(question, **kw):
        seen.update(kw, question=question)
        return {"question": question, "mode": "demo"}

    monkeypatch.setattr(main, "ask", fake_ask)
    res = client.post("/api/v1/ask", json={"question": "  Top cities?  "})
    assert res.status_code == 200
    assert seen["question"] == "Top cities?"
    assert seen["max_rows"] == 200 and seen["timeout_ms"] == 5000 and seen["llm"] is None


@pytest.mark.parametrize("question", ["", "hi", "x" * 301])
def test_ask_validates_question_length(client, question):
    assert client.post("/api/v1/ask", json={"question": question}).status_code == 422


@pytest.mark.parametrize(
    ("error", "status"), [(AskError("bad sql"), 422), (AskUnavailable("demo"), 503)]
)
def test_ask_errors_map_to_status_codes(client, monkeypatch, error, status):
    def fake_ask(question, **kw):
        raise error

    monkeypatch.setattr(main, "ask", fake_ask)
    res = client.post("/api/v1/ask", json={"question": "Top cities?"})
    assert res.status_code == status
    assert res.json()["detail"] == str(error)


def test_cors_allows_configured_origin(client):
    res = client.options(
        "/api/health",
        headers={"Origin": "https://   cartlens-bice.vercel.app", "Access-Control-Request-Method": "GET"},
    )
    assert res.headers["access-control-allow-origin"] == "https://   cartlens-bice.vercel.app"
