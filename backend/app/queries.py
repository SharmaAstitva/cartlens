"""All SQL the API runs. Every function takes an open psycopg connection (dict rows)."""

from __future__ import annotations

from datetime import date

from psycopg.rows import dict_row, tuple_row

from app.sql_guard import ALLOWED_SCHEMA, ALLOWED_TABLES

COUNTS = {
    "raw_events": "raw.events",
    "quarantined": "raw.quarantine",
    "orders": "analytics.fct_orders",
    "customers": "analytics.dim_customers",
}


def _all(conn, sql: str, params=None) -> list[dict]:
    with conn.cursor(row_factory=dict_row) as cur:
        return cur.execute(sql, params).fetchall()


def _one(conn, sql: str, params=None) -> dict | None:
    with conn.cursor(row_factory=dict_row) as cur:
        return cur.execute(sql, params).fetchone()


def health_snapshot(conn) -> dict:
    counts = {}
    for key, table in COUNTS.items():
        exists = _one(conn, "select to_regclass(%s) is not null as ok", (table,))["ok"]
        counts[key] = _one(conn, f"select count(*) as n from {table}")["n"] if exists else None
    last_run = None
    if _one(conn, "select to_regclass('ops.pipeline_runs') is not null as ok")["ok"]:
        last_run = _one(
            conn,
            "select run_id, status, finished_at, window_start, window_end, events_inserted, "
            "dbt_tests_passed, dbt_tests_failed from ops.pipeline_runs order by run_id desc limit 1",
        )
    through = None
    if counts["orders"] is not None:
        through = _one(conn, "select max(date) as d from analytics.fct_daily_kpis")["d"]
    return {"counts": counts, "last_run": last_run, "data_through": through}


def _period_totals(conn, days: int) -> tuple[date, dict[str, dict]]:
    daily = _all(
        conn,
        """
        with bounds as (select max(date) as through from analytics.fct_daily_kpis)
        select case when k.date > b.through - %(days)s then 'current' else 'previous' end as period,
               sum(k.sessions) as sessions, sum(k.orders) as orders, sum(k.net_revenue) as net_revenue
        from analytics.fct_daily_kpis k, bounds b
        where k.date > b.through - 2 * %(days)s
        group by 1
        """,
        {"days": days},
    )
    buyers = _all(
        conn,
        """
        with bounds as (select max(date) as through from analytics.fct_daily_kpis)
        select case when o.order_date > b.through - %(days)s then 'current' else 'previous' end as period,
               count(distinct o.customer_id) as customers,
               count(distinct o.customer_id) filter (where o.customer_order_number > 1)
                   as returning_customers
        from analytics.fct_orders o, bounds b
        where o.order_date > b.through - 2 * %(days)s
        group by 1
        """,
        {"days": days},
    )
    through = _one(conn, "select max(date) as d from analytics.fct_daily_kpis")["d"]
    totals = {}
    for period in ("current", "previous"):
        d = next((r for r in daily if r["period"] == period), {})
        b = next((r for r in buyers if r["period"] == period), {})
        orders, sessions = int(d.get("orders") or 0), int(d.get("sessions") or 0)
        revenue = float(d.get("net_revenue") or 0)
        customers, returning = int(b.get("customers") or 0), int(b.get("returning_customers") or 0)
        totals[period] = {
            "net_revenue": revenue,
            "orders": orders,
            "sessions": sessions,
            "customers": customers,
            "returning_customers": returning,
            "avg_order_value": round(revenue / orders, 2) if orders else None,
            "conversion_rate": round(orders / sessions, 4) if sessions else None,
            "repeat_rate": round(returning / customers, 4) if customers else None,
        }
    return through, totals


def kpis(conn, days: int) -> dict:
    through, totals = _period_totals(conn, days)
    series = _all(
        conn,
        "select date, net_revenue::float as net_revenue, orders, sessions "
        "from analytics.fct_daily_kpis where date > %s - %s order by date",
        (through, days),
    )
    return {"through": through, "days": days, **totals, "series": series}


def cities(conn, limit: int) -> list[dict]:
    return _all(
        conn,
        "select city, state, customers, repeat_customers, repeat_rate::float as repeat_rate, "
        "orders, net_revenue::float as net_revenue, avg_order_value::float as avg_order_value "
        "from analytics.mart_city_summary order by net_revenue desc limit %s",
        (limit,),
    )


def funnel(conn, months: int) -> list[dict]:
    return _all(
        conn,
        "select * from (select * from analytics.mart_funnel_monthly order by month desc limit %s) m "
        "order by month",
        (months,),
    )


def cohorts(conn, months: int) -> list[dict]:
    return _all(
        conn,
        """
        select cohort_month, month_number, cohort_size, active_customers,
               retention_rate::float as retention_rate
        from analytics.mart_cohort_retention
        where cohort_month in (
            select distinct cohort_month from analytics.mart_cohort_retention
            order by cohort_month desc limit %s)
        order by cohort_month, month_number
        """,
        (months,),
    )


def segments(conn) -> list[dict]:
    return _all(
        conn,
        """
        select segment, count(*) as customers, sum(monetary)::float as net_revenue,
               round(avg(recency_days), 1)::float as avg_recency_days,
               round(avg(frequency), 2)::float as avg_orders
        from analytics.mart_rfm group by segment order by net_revenue desc
        """,
    )


def pipeline_runs(conn, limit: int) -> list[dict]:
    return _all(conn, "select * from ops.pipeline_runs order by run_id desc limit %s", (limit,))


def data_range(conn) -> tuple[date, date]:
    row = _one(conn, "select min(date) as first, max(date) as last from analytics.fct_daily_kpis")
    return row["first"], row["last"]


def describe_marts(conn) -> str:
    """Tables and columns the LLM may use, with the descriptions dbt wrote as comments."""
    rows = _all(
        conn,
        """
        select c.table_name, c.column_name, c.data_type,
               obj_description(format('%%I.%%I', c.table_schema, c.table_name)::regclass) as table_doc,
               col_description(format('%%I.%%I', c.table_schema, c.table_name)::regclass,
                               c.ordinal_position) as column_doc
        from information_schema.columns c
        where c.table_schema = %s and c.table_name = any(%s)
        order by c.table_name, c.ordinal_position
        """,
        (ALLOWED_SCHEMA, sorted(ALLOWED_TABLES)),
    )
    lines, current = [], None
    for r in rows:
        if r["table_name"] != current:
            current = r["table_name"]
            lines.append(f"\nTable {current}: {r['table_doc'] or ''}".rstrip())
        doc = f" -- {r['column_doc']}" if r["column_doc"] else ""
        lines.append(f"  {r['column_name']} {r['data_type']}{doc}")
    return "\n".join(lines).strip()


def run_readonly(conn, sql: str, max_rows: int, timeout_ms: int):
    """Run guarded SQL in a read-only transaction with a timeout and a row cap.

    Returns (columns, rows, truncated).
    """
    with conn.transaction(), conn.cursor(row_factory=tuple_row) as cur:
        cur.execute("set transaction read only")
        cur.execute(f"set local statement_timeout = {int(timeout_ms)}")
        cur.execute(f"set local search_path = {ALLOWED_SCHEMA}")
        cur.execute(f"select * from ({sql}) as answer limit {int(max_rows) + 1}")  # noqa: S608
        columns = [c.name for c in cur.description]
        rows = [list(r) for r in cur.fetchall()]
    return columns, rows[:max_rows], len(rows) > max_rows
