"""The daily pipeline, orchestrated with Prefect.

    extract + load  ->  dbt build (models + tests)  ->  record the run

Run it with:  python -m pipeline.flow  [--as-of YYYY-MM-DD] [--backfill-days N] [--scale X]
"""

from __future__ import annotations

import argparse
import os
from dataclasses import asdict
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

import psycopg
from prefect import flow, get_run_logger, task

from pipeline.generator import IST, generate_batch
from pipeline.ingest import ensure_schema, ingest

DBT_DIR = Path(__file__).resolve().parent.parent / "dbt"
DEFAULT_DB = "postgresql://cartlens:cartlens@localhost:5432/cartlens"


def compute_window(last_loaded: date | None, as_of: date, backfill_days: int):
    """Which arrival days to load: everything after the last loaded day, up to yesterday."""
    end = as_of - timedelta(days=1)
    start = (
        last_loaded + timedelta(days=1) if last_loaded else as_of - timedelta(days=backfill_days)
    )
    return (start, end) if start <= end else None


def dbt_env(database_url: str) -> dict[str, str]:
    """Translate DATABASE_URL into the DBT_* variables that dbt/profiles.yml reads."""
    url = urlparse(database_url)
    if url.scheme not in ("postgres", "postgresql") or not url.hostname:
        raise ValueError("DATABASE_URL must look like postgresql://user:password@host:port/dbname")
    return {
        "DBT_HOST": url.hostname,
        "DBT_PORT": str(url.port or 5432),
        "DBT_USER": unquote(url.username or ""),
        "DBT_PASSWORD": unquote(url.password or ""),
        "DBT_DBNAME": url.path.lstrip("/"),
        "DBT_SSLMODE": parse_qs(url.query).get("sslmode", ["prefer"])[0],
    }


def summarize_dbt(results) -> dict[str, int]:
    """Count built nodes and test outcomes from dbt's run results."""
    built = sum(1 for r in results if r.node.resource_type != "test" and r.status == "success")
    passed = sum(1 for r in results if r.node.resource_type == "test" and r.status == "pass")
    failed = sum(
        1 for r in results if r.node.resource_type == "test" and r.status in ("fail", "error")
    )
    return {"models_ok": built, "tests_passed": passed, "tests_failed": failed}


def last_loaded_day(conn: psycopg.Connection) -> date | None:
    return conn.execute("select max(window_end) from ops.pipeline_runs").fetchone()[0]


def record_run(conn: psycopg.Connection, **run) -> None:
    cols = ", ".join(run)
    conn.execute(
        f"insert into ops.pipeline_runs ({cols}) values ({', '.join(['%s'] * len(run))})",
        list(run.values()),
    )


@task(retries=2, retry_delay_seconds=10)
def extract_and_load(database_url: str, as_of: date, backfill_days: int, scale: float) -> dict:
    logger = get_run_logger()
    with psycopg.connect(database_url, autocommit=True) as conn:
        ensure_schema(conn)
        window = compute_window(last_loaded_day(conn), as_of, backfill_days)
        if window is None:
            logger.info("Already loaded up to %s; nothing new to load", as_of - timedelta(days=1))
            return {"window": None}
        events = generate_batch(*window, scale=scale)
        stats = ingest(conn, events, batch_id=f"{window[0]}..{window[1]}")
    logger.info("Loaded window %s..%s: %s", *window, stats)
    return {"window": window, **asdict(stats)}


@task
def transform(database_url: str) -> dict:
    """dbt build = seeds + models + data tests, in dependency order."""
    from dbt.cli.main import dbtRunner  # heavy import, only needed here

    os.environ.update(dbt_env(database_url))
    res = dbtRunner().invoke(
        ["build", "--project-dir", str(DBT_DIR), "--profiles-dir", str(DBT_DIR)]
    )
    summary = summarize_dbt(res.result.results if res.result else [])
    if not res.success:
        raise RuntimeError(f"dbt build failed: {summary} {res.exception or ''}".strip())
    return summary


@flow(name="cartlens-daily")
def cartlens_daily(
    as_of: date | None = None,
    backfill_days: int = 365,
    scale: float = 1.0,
    database_url: str | None = None,
) -> dict:
    database_url = database_url or os.environ.get("DATABASE_URL", DEFAULT_DB)
    as_of = as_of or datetime.now(IST).date()
    started = datetime.now(UTC)
    run = {"as_of": as_of, "status": "failed"}
    try:
        loaded = extract_and_load(database_url, as_of, backfill_days, scale)
        if loaded["window"]:
            run.update(
                window_start=loaded["window"][0],
                window_end=loaded["window"][1],
                events_received=loaded["received"],
                events_inserted=loaded["inserted"],
                events_duplicate=loaded["duplicate"],
                events_quarantined=loaded["quarantined"],
            )
            built = transform(database_url)
            run.update(
                dbt_models_ok=built["models_ok"],
                dbt_tests_passed=built["tests_passed"],
                dbt_tests_failed=built["tests_failed"],
                status="success",
            )
        else:
            run["status"] = "up_to_date"
        return run
    except Exception as exc:
        run["error"] = str(exc)[:2000]
        raise
    finally:
        with psycopg.connect(database_url, autocommit=True) as conn:
            ensure_schema(conn)
            record_run(conn, started_at=started, finished_at=datetime.now(UTC), **run)


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description="Run the CartLens pipeline once.")
    parser.add_argument(
        "--as-of",
        type=date.fromisoformat,
        default=None,
        help="treat this date as today (default: today in IST)",
    )
    parser.add_argument(
        "--backfill-days", type=int, default=365, help="days of history to load on the first run"
    )
    parser.add_argument("--scale", type=float, default=1.0, help="traffic multiplier")
    return parser.parse_args(argv)


if __name__ == "__main__":  # pragma: no cover
    args = parse_args()
    cartlens_daily(as_of=args.as_of, backfill_days=args.backfill_days, scale=args.scale)
