"""Loading into Postgres: dedupe on event_id, quarantine, idempotency."""

from pipeline.ingest import ensure_schema, ingest


def event(event_id, **extra):
    return {
        "event_id": event_id,
        "event_type": "page_view",
        "ts": "2026-03-01T10:00:00+05:30",
        "customer_id": "C00001",
        "session_id": "S-test",
        **extra,
    }


def count(conn, sql, *params):
    return conn.execute(sql, params).fetchone()[0]


def test_ensure_schema_is_idempotent(conn):
    ensure_schema(conn)
    ensure_schema(conn)
    assert (
        count(
            conn,
            "select count(*) from information_schema.schemata where schema_name in ('raw', 'ops')",
        )
        == 2
    )


def test_loads_valid_events_drops_duplicates_and_quarantines_bad_ones(conn):
    batch = [event("t-1"), event("t-1"), event("t-2"), event("t-3", customer_id=None)]
    stats = ingest(conn, batch, "test-batch")
    assert (stats.received, stats.inserted, stats.duplicate, stats.quarantined) == (4, 2, 1, 1)
    assert count(conn, "select count(*) from raw.events where event_id like 't-%%'") == 2
    reason = count(conn, "select reason from raw.quarantine where batch_id = 'test-batch'")
    assert "customer_id" in reason


def test_reloading_the_same_batch_changes_nothing(conn):
    batch = [event("t-10"), event("t-11"), event("t-12", event_type="bogus")]
    ingest(conn, batch, "b1")
    again = ingest(conn, batch, "b1")
    assert (again.inserted, again.duplicate, again.quarantined) == (0, 2, 1)
    assert count(conn, "select count(*) from raw.quarantine where batch_id = 'b1'") == 1


def test_payload_is_stored_as_received(conn):
    ingest(conn, [event("t-20", price="₹1,299.00", city=" MUMBAI")], "b2")
    payload = count(conn, "select payload from raw.events where event_id = 't-20'")
    assert payload["price"] == "₹1,299.00" and payload["city"] == " MUMBAI"
