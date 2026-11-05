"""Unit tests for the SQL guard that sits between the LLM and the database."""

import pytest

from app.sql_guard import ALLOWED_TABLES, UnsafeSQLError, guard_sql


@pytest.mark.parametrize(
    "sql",
    [
        "select city, count(*) from fct_orders group by city",
        "SELECT * FROM analytics.dim_customers",
        "with recent as (select * from fct_orders where order_date > current_date - 30) "
        "select city, sum(net_revenue) from recent group by city",
        "select o.city, c.lifetime_net_revenue from fct_orders o join dim_customers c using (customer_id)",
        "select segment, count(*) from mart_rfm group by 1 union all select 'total', count(*) from mart_rfm",
        "select g from generate_series(1, 3) as g",
        "select date_trunc('month', order_date) as month, sum(net_revenue) from fct_orders group by 1",
    ],
)
def test_allows_read_only_queries_on_marts(sql):
    assert guard_sql(sql)


@pytest.mark.parametrize(
    ("sql", "reason"),
    [
        ("", "empty"),
        ("   ", "empty"),
        ("this is not sql at all )(", "parse"),
        ("insert into fct_orders values (1)", "SELECT"),
        ("update dim_customers set city = 'x'", "SELECT"),
        ("delete from fct_orders", "SELECT"),
        ("drop table fct_orders", "SELECT"),
        ("truncate fct_orders", "SELECT"),
        ("set statement_timeout = 0", "SELECT"),
        ("copy fct_orders to stdout", "SELECT"),
        ("grant all on fct_orders to public", "SELECT"),
        ("select 1; select 2", "one statement"),
        ("select 1; drop table fct_orders", "one statement"),
        ("select * from raw.events", "raw.events"),
        ("select * from ops.pipeline_runs", "ops.pipeline_runs"),
        ("select * from pg_catalog.pg_user", "pg_catalog"),
        ("select * from information_schema.tables", "information_schema"),
        ("select * from pg_user", "pg_user"),
        ("select * from stg_events", "stg_events"),
        ("select pg_sleep(10)", "pg_sleep"),
        ("select * from dblink('host=evil', 'select 1') as t(x int)", "dblink"),
        ("select set_config('statement_timeout', '0', false)", "set_config"),
        ("select * into stolen from fct_orders", "INTO"),
        ("select * from fct_orders for update", "lock"),
        ("with x as (select * from raw.events) select * from x", "raw.events"),
    ],
)
def test_rejects_unsafe_queries(sql, reason):
    with pytest.raises(UnsafeSQLError, match=f"(?i){reason}"):
        guard_sql(sql)


def test_cte_named_like_allowed_table_does_not_hide_forbidden_source():
    with pytest.raises(UnsafeSQLError):
        guard_sql("with fct_orders as (select * from raw.events) select * from fct_orders")


def test_returns_normalised_pretty_sql():
    out = guard_sql("select city,count(*) as n from fct_orders group by city")
    assert out.startswith("SELECT")
    assert "\n" in out


def test_allowlist_contains_only_marts():
    assert "fct_orders" in ALLOWED_TABLES
    assert not any(t.startswith(("stg_", "raw")) for t in ALLOWED_TABLES)
