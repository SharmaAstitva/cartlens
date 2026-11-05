"""Validate raw events and land them in Postgres.

Valid events go to raw.events (deduplicated on event_id); invalid ones go to
raw.quarantine with the reason, instead of being silently dropped.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import psycopg
from pydantic import BaseModel, ConfigDict, Field, ValidationError

SCHEMA_SQL = (Path(__file__).parent / "schema.sql").read_text(encoding="utf-8")


class RawEvent(BaseModel):
    """The minimum contract an event must meet. Value cleaning happens in dbt."""

    model_config = ConfigDict(extra="allow")
    event_id: str = Field(min_length=1)
    event_type: Literal[
        "page_view", "add_to_cart", "checkout_started", "order_placed", "order_refunded"
    ]
    ts: str = Field(min_length=1)
    customer_id: str = Field(min_length=1)
    session_id: str = Field(min_length=1)


@dataclass
class IngestStats:
    received: int
    inserted: int
    duplicate: int
    quarantined: int


def validate_event(payload) -> str | None:
    """Return None if the event is valid, otherwise a short reason."""
    try:
        RawEvent.model_validate(payload)
    except ValidationError as exc:
        return "; ".join(
            f"{'.'.join(map(str, e['loc'])) or 'payload'}: {e['msg']}" for e in exc.errors()
        )
    return None


def payload_hash(payload: dict) -> str:
    return hashlib.sha1(json.dumps(payload, sort_keys=True, default=str).encode()).hexdigest()


def ensure_schema(conn: psycopg.Connection) -> None:
    conn.execute(SCHEMA_SQL)


def ingest(conn: psycopg.Connection, events: list[dict], batch_id: str) -> IngestStats:
    good, bad = [], []
    for event in events:
        reason = validate_event(event)
        (bad if reason else good).append((event, reason))

    with conn.transaction(), conn.cursor() as cur:
        cur.execute("create temp table incoming (event_id text, payload jsonb) on commit drop")
        with cur.copy("copy incoming (event_id, payload) from stdin") as copy:
            for event, _ in good:
                copy.write_row((event["event_id"], json.dumps(event)))
        cur.execute(
            "insert into raw.events (event_id, payload, batch_id) "
            "select event_id, payload, %s from incoming on conflict (event_id) do nothing",
            (batch_id,),
        )
        inserted = cur.rowcount
        cur.executemany(
            "insert into raw.quarantine (payload_hash, payload, reason, batch_id) "
            "values (%s, %s, %s, %s) on conflict (payload_hash) do nothing",
            [(payload_hash(e), json.dumps(e), r, batch_id) for e, r in bad],
        )
    return IngestStats(len(events), inserted, len(good) - inserted, len(bad))
