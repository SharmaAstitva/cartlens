"""Unit tests for the synthetic event generator.

The generator is deterministic: the same window always yields the same events.
That makes the pipeline idempotent and lets these tests use fixed dates
(never today's date).
"""

import re
from collections import Counter
from datetime import UTC, date, datetime, timedelta, timezone

from pipeline.generator import EVENT_TYPES, generate_batch

IST = timezone(timedelta(hours=5, minutes=30))
START, END = date(2026, 3, 1), date(2026, 3, 14)


def parse_ts(value: str) -> datetime:
    """Test helper that mirrors the dbt `parse_ts` macro."""
    if re.fullmatch(r"\d{13}", value):
        return datetime.fromtimestamp(int(value) / 1000, tz=UTC)
    if re.fullmatch(r"\d{2}/\d{2}/\d{4} \d{2}:\d{2}:\d{2}", value):
        return datetime.strptime(value, "%d/%m/%Y %H:%M:%S").replace(tzinfo=IST)
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def ist_date(event: dict) -> date:
    return parse_ts(event["ts"]).astimezone(IST).date()


def batch(start=START, end=END, scale=0.5):
    return generate_batch(start, end, scale=scale)


def test_same_window_gives_identical_events():
    assert batch() == batch()


def test_every_event_type_appears():
    types = {e["event_type"] for e in batch()}
    assert set(EVENT_TYPES) <= types


def test_events_never_come_from_after_the_window():
    # Late arrivals mean an event can be from the day before the window,
    # but nothing may be from after it.
    for event in batch():
        if "ts" in event:
            assert START - timedelta(days=1) <= ist_date(event) <= END


def test_adjacent_windows_partition_a_longer_window():
    """Loading two windows back to back must equal loading the combined window.

    This is what makes daily runs safe: no event is lost or loaded twice
    across run boundaries, including late arrivals and delayed refunds.
    """
    first = batch(START, date(2026, 3, 7))
    second = batch(date(2026, 3, 8), END)
    combined = batch(START, END)
    key = lambda e: (e["event_id"], e["event_type"], e.get("order_id"))  # noqa: E731
    assert Counter(map(key, first + second)) == Counter(map(key, combined))


def test_contains_messy_real_world_data():
    events = batch()
    stamps = [e["ts"] for e in events if "ts" in e]
    assert any(s.endswith("Z") for s in stamps)
    assert any(s.endswith("+05:30") for s in stamps)
    assert any(re.fullmatch(r"\d{13}", s) for s in stamps)
    assert any("/" in s for s in stamps)

    prices = [e["price"] for e in events if "price" in e]
    assert any(isinstance(p, str) and p.startswith("₹") for p in prices)
    assert any(isinstance(p, float) for p in prices)

    cities = {e.get("city") for e in events}
    assert {"Bangalore", "Bengaluru"} <= cities or {"Bombay", "Mumbai"} <= cities


def test_contains_duplicates_and_invalid_rows():
    events = batch(scale=1.0)
    ids = Counter(e["event_id"] for e in events)
    assert any(n > 1 for n in ids.values()), "expected exact duplicate deliveries"

    orders = Counter(e["order_id"] for e in events if e["event_type"] == "order_placed")
    assert any(n > 1 for n in orders.values()), "expected double-submitted orders"

    invalid = [e for e in events if not e.get("customer_id") or e["event_type"] not in EVENT_TYPES]
    assert invalid, "expected a few malformed events for the quarantine"


def test_orders_carry_what_the_models_need():
    orders = [e for e in batch() if e["event_type"] == "order_placed"]
    assert orders
    for o in orders:
        assert o["order_id"].startswith("ORD-")
        assert o["quantity"] >= 1
        assert o["product_id"] and o["category"] and o["city"] and o["channel"]


def test_scale_controls_volume():
    small = len(batch(scale=0.2))
    large = len(batch(scale=1.0))
    assert small < large / 2


def test_customers_return_over_time():
    events = batch(date(2026, 1, 1), date(2026, 3, 31), scale=0.5)
    per_customer = Counter(e["customer_id"] for e in events if e["event_type"] == "order_placed")
    assert sum(1 for n in per_customer.values() if n > 1) > 10
