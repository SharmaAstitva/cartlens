"""The API against the database built by the real pipeline."""

import psycopg
import pytest
from fastapi.testclient import TestClient

from app import queries
from app.ask import EXAMPLES
from app.config import load_settings
from app.main import create_app

from .conftest import AS_OF


@pytest.fixture(scope="module")
def client(built_db):
    app = create_app(load_settings({"DATABASE_URL": built_db["url"]}))
    with TestClient(app) as test_client:  # runs the lifespan, so the real pool opens
        yield test_client


def get(client, path):
    res = client.get(path)
    assert res.status_code == 200, res.text
    return res.json()


def test_health_reports_counts_and_last_run(client):
    body = get(client, "/api/health")
    assert body["status"] == "ok"
    assert body["counts"]["raw_events"] > 1000
    assert body["counts"]["orders"] > 100
    assert body["counts"]["quarantined"] > 0
    assert body["last_run"]["status"] == "success"
    assert body["data_through"] == AS_OF.isoformat()
    assert body["llm"]["mode"] == "demo"


def test_kpis_compare_two_periods(client):
    body = get(client, "/api/v1/kpis?days=30")
    assert body["through"] == AS_OF.isoformat()
    assert len(body["series"]) == 30
    current, previous = body["current"], body["previous"]
    assert current["orders"] > 0 and previous["orders"] > 0
    assert current["net_revenue"] == pytest.approx(sum(d["net_revenue"] for d in body["series"]))
    assert 0 < current["conversion_rate"] < 1
    assert 0 <= current["repeat_rate"] <= 1
    assert current["avg_order_value"] == pytest.approx(
        current["net_revenue"] / current["orders"], 0.01
    )


def test_cities_are_ranked_by_revenue(client):
    rows = get(client, "/api/v1/cities?limit=5")
    assert 0 < len(rows) <= 5
    revenue = [r["net_revenue"] for r in rows]
    assert revenue == sorted(revenue, reverse=True)


def test_funnel_narrows_each_month(client):
    rows = get(client, "/api/v1/funnel?months=3")
    assert len(rows) == 3
    for r in rows:
        assert r["sessions_viewed"] >= r["sessions_added_to_cart"] >= r["sessions_checked_out"]
        assert r["sessions_checked_out"] >= r["sessions_ordered"] > 0


def test_cohorts_start_at_full_retention(client):
    rows = get(client, "/api/v1/cohorts?months=4")
    assert {r["cohort_month"] for r in rows} and len({r["cohort_month"] for r in rows}) <= 4
    assert all(r["retention_rate"] == 1 for r in rows if r["month_number"] == 0)


def test_segments_cover_every_customer(client, built_db):
    rows = get(client, "/api/v1/segments")
    with psycopg.connect(built_db["url"]) as conn:
        customers = conn.execute("select count(*) from analytics.dim_customers").fetchone()[0]
    assert sum(r["customers"] for r in rows) == customers


def test_pipeline_runs_newest_first(client):
    runs = get(client, "/api/v1/pipeline/runs?limit=10")
    assert [r["status"] for r in runs] == ["success", "up_to_date", "success"]


@pytest.mark.parametrize("example", EXAMPLES, ids=lambda e: e["question"][:40])
def test_every_demo_question_runs_on_real_data(client, example):
    res = client.post("/api/v1/ask", json={"question": example["question"]})
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["mode"] == "demo" and body["rows"], body
    chart = body["chart"]
    if chart["type"] in ("bar", "line"):
        assert {chart["x"], chart["y"]} <= set(body["columns"])


def test_llm_sql_cannot_escape_the_guard(client):
    class EvilLLM:
        def complete_json(self, system, user, schema):
            return {
                "sql": "select * from raw.events",
                "chart": {"type": "table", "x": None, "y": None},
                "explanation": "x",
            }

    client.app.state.llm = EvilLLM()
    try:
        res = client.post("/api/v1/ask", json={"question": "Show me everything"})
    finally:
        client.app.state.llm = None
    assert res.status_code == 422
    assert "raw.events" in res.json()["detail"]


def test_readonly_execution_blocks_writes_even_without_the_guard(built_db):
    with (
        psycopg.connect(built_db["url"], autocommit=True) as conn,
        pytest.raises(psycopg.errors.ReadOnlySqlTransaction),
    ):
        queries.run_readonly(conn, "select nextval('ops.pipeline_runs_run_id_seq')", 10, 5000)


def test_slow_queries_are_cancelled(built_db):
    with (
        psycopg.connect(built_db["url"], autocommit=True) as conn,
        pytest.raises(psycopg.errors.QueryCanceled),
    ):
        queries.run_readonly(conn, "select pg_sleep(2)", 10, 200)


def test_results_are_truncated_at_max_rows(built_db):
    with psycopg.connect(built_db["url"], autocommit=True) as conn:
        cols, rows, truncated = queries.run_readonly(conn, "select * from fct_orders", 5, 5000)
    assert len(rows) == 5 and truncated and "order_id" in cols
