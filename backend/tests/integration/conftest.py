"""Integration tests run against a real Postgres (docker compose locally, a service container in CI)."""

import os
from datetime import date, timedelta

import psycopg
import pytest

TEST_DB = os.environ.get(
    "TEST_DATABASE_URL", "postgresql://cartlens:cartlens@localhost:5432/cartlens_test"
)
AS_OF = date(2026, 3, 1)  # fixed "today": tests never depend on the real date
BACKFILL_DAYS = 120
SCALE = 0.25


@pytest.fixture(scope="session")
def db_url():
    try:
        psycopg.connect(TEST_DB, connect_timeout=3).close()
    except psycopg.OperationalError as exc:
        pytest.fail(
            f"Integration tests need Postgres at {TEST_DB}.\n"
            f"Start it with:  docker compose up -d db\n{exc}"
        )
    return TEST_DB


@pytest.fixture(scope="session")
def built_db(db_url):
    """Run the real Prefect flow three times and share the resulting database.

    1. first run on an empty database: backfill + dbt build
    2. same day again: nothing new, nothing loaded
    3. next day: loads exactly one day
    """
    from prefect.testing.utilities import prefect_test_harness

    from pipeline.flow import cartlens_daily

    with psycopg.connect(db_url, autocommit=True) as conn:
        conn.execute("drop schema if exists raw, ops, analytics, analytics_staging cascade")

    kwargs = {"backfill_days": BACKFILL_DAYS, "scale": SCALE, "database_url": db_url}
    with prefect_test_harness():
        runs = [
            cartlens_daily(as_of=AS_OF, **kwargs),
            cartlens_daily(as_of=AS_OF, **kwargs),
            cartlens_daily(as_of=AS_OF + timedelta(days=1), **kwargs),
        ]
    return {"url": db_url, "runs": runs}


@pytest.fixture
def conn(built_db):
    """A connection whose changes are rolled back after the test."""
    with psycopg.connect(built_db["url"]) as connection:
        yield connection
        connection.rollback()
