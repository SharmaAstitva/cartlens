"""End to end: the Prefect flow loads data, dbt builds and tests the models."""

from datetime import timedelta

from app import queries
from app.sql_guard import ALLOWED_TABLES
from pipeline.generator import CITIES

from .conftest import AS_OF, BACKFILL_DAYS


def one(conn, sql):
    return conn.execute(sql).fetchone()[0]


def test_first_run_backfills_and_passes_all_dbt_tests(built_db):
    first = built_db["runs"][0]
    assert first["status"] == "success"
    assert first["window_start"] == AS_OF - timedelta(days=BACKFILL_DAYS)
    assert first["window_end"] == AS_OF - timedelta(days=1)
    assert first["events_inserted"] > 1000
    assert first["events_duplicate"] > 0, "duplicate deliveries should be dropped"
    assert first["events_quarantined"] > 0, "malformed events should be quarantined"
    assert first["dbt_tests_failed"] == 0
    assert first["dbt_tests_passed"] >= 30


def test_rerun_on_same_day_loads_nothing(built_db):
    assert built_db["runs"][1]["status"] == "up_to_date"


def test_next_day_loads_exactly_one_day(built_db):
    third = built_db["runs"][2]
    assert third["status"] == "success"
    assert third["window_start"] == third["window_end"] == AS_OF
    assert 0 < third["events_inserted"] < built_db["runs"][0]["events_inserted"] / 50


def test_every_run_is_recorded(conn):
    statuses = [r[0] for r in conn.execute("select status from ops.pipeline_runs order by run_id")]
    assert statuses == ["success", "up_to_date", "success"]


def test_double_submitted_orders_are_counted_once(conn):
    raw_orders = one(
        conn,
        "select count(distinct payload->>'order_id') from raw.events "
        "where payload->>'event_type' = 'order_placed'",
    )
    raw_order_events = one(
        conn, "select count(*) from raw.events where payload->>'event_type' = 'order_placed'"
    )
    assert raw_order_events > raw_orders, "the feed should contain double submits"
    assert one(conn, "select count(*) from analytics.fct_orders") == raw_orders


def test_cities_are_standardised(conn):
    cities = {r[0] for r in conn.execute("select distinct city from analytics.fct_orders")}
    assert cities <= {c for c, _, _ in CITIES}
    assert "Bangalore" not in cities and "Bombay" not in cities


def test_all_timestamp_formats_are_parsed(conn):
    assert (
        one(conn, "select count(*) from analytics_staging.stg_events where occurred_at is null")
        == 0
    )
    latest = one(conn, "select max(order_date) from analytics.fct_orders")
    assert latest == AS_OF


def test_marts_are_populated(conn):
    for table in ALLOWED_TABLES:
        assert one(conn, f"select count(*) from analytics.{table}") > 0, table


def test_column_descriptions_reach_postgres(conn):
    schema = queries.describe_marts(conn)
    assert "fct_orders" in schema and "mart_rfm" in schema
    assert "Use this for revenue questions" in schema
