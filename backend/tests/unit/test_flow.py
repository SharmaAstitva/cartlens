"""Unit tests for the pure helpers behind the Prefect flow."""

from datetime import date
from types import SimpleNamespace

import pytest

from pipeline.flow import compute_window, dbt_env, parse_args, summarize_dbt

AS_OF = date(2026, 3, 10)


def test_first_run_backfills():
    assert compute_window(None, AS_OF, backfill_days=30) == (date(2026, 2, 8), date(2026, 3, 9))


def test_next_run_loads_only_new_days():
    assert compute_window(date(2026, 3, 8), AS_OF, 30) == (date(2026, 3, 9), date(2026, 3, 9))


def test_missed_runs_are_caught_up():
    assert compute_window(date(2026, 3, 5), AS_OF, 30) == (date(2026, 3, 6), date(2026, 3, 9))


def test_up_to_date_returns_none():
    assert compute_window(date(2026, 3, 9), AS_OF, 30) is None


def test_dbt_env_from_local_url():
    env = dbt_env("postgresql://cartlens:cartlens@localhost:5432/cartlens")
    assert env == {
        "DBT_HOST": "localhost",
        "DBT_PORT": "5432",
        "DBT_USER": "cartlens",
        "DBT_PASSWORD": "cartlens",
        "DBT_DBNAME": "cartlens",
        "DBT_SSLMODE": "prefer",
    }


def test_dbt_env_from_neon_style_url():
    env = dbt_env(
        "postgresql://app:p%40ss@ep-x.neon.tech/neondb?sslmode=require&channel_binding=require"
    )
    assert env["DBT_PASSWORD"] == "p@ss"
    assert env["DBT_PORT"] == "5432"
    assert env["DBT_SSLMODE"] == "require"


def test_dbt_env_rejects_garbage():
    with pytest.raises(ValueError):
        dbt_env("not a url")


def result(resource_type, status):
    return SimpleNamespace(node=SimpleNamespace(resource_type=resource_type), status=status)


def test_summarize_dbt_counts_models_and_tests():
    summary = summarize_dbt(
        [
            result("model", "success"),
            result("model", "success"),
            result("seed", "success"),
            result("test", "pass"),
            result("test", "pass"),
            result("test", "fail"),
            result("test", "error"),
            result("model", "skipped"),
        ]
    )
    assert summary == {"models_ok": 3, "tests_passed": 2, "tests_failed": 2}


def test_parse_args_defaults_and_values():
    args = parse_args([])
    assert args.as_of is None and args.backfill_days == 365 and args.scale == 1.0
    args = parse_args(["--as-of", "2026-03-10", "--backfill-days", "30", "--scale", "0.2"])
    assert args.as_of == date(2026, 3, 10) and args.backfill_days == 30 and args.scale == 0.2
