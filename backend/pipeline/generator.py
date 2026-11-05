"""Deterministic synthetic e-commerce events for a fictional Indian D2C store.

Every day's events are derived from a seed made of the date, so any window
can be regenerated exactly. That makes loading idempotent and lets daily
runs and backfills produce the same rows.

The data is messy on purpose, like real tracking feeds:
mixed timestamp formats, prices as strings, city spelling variants,
duplicate deliveries, double-submitted orders, late-arriving events and a
few malformed rows. Cleaning it is the job of the ingest step and dbt.
"""

from __future__ import annotations

import hashlib
import random
from bisect import bisect_right
from datetime import UTC, date, datetime, timedelta, timezone
from functools import cache
from itertools import accumulate

IST = timezone(timedelta(hours=5, minutes=30))
EPOCH = date(2025, 1, 1)  # store launch; the customer pool is anchored here
EVENT_TYPES = ("page_view", "add_to_cart", "checkout_started", "order_placed", "order_refunded")
N_CUSTOMERS = 25000
SESSIONS_PER_DAY = 400
LATE_SHARE = 0.02  # events delivered a day after they happened
LOOKBACK_DAYS = 4  # refunds land up to 3 days after the order, plus 1 day of lateness

# (canonical city, traffic weight, spellings seen in the feed)
CITIES = [
    ("Mumbai", 14, ["Mumbai", "mumbai", "Bombay", " MUMBAI"]),
    ("Delhi", 13, ["Delhi", "New Delhi", "delhi "]),
    ("Bengaluru", 13, ["Bengaluru", "Bangalore", "bangalore", "BLR"]),
    ("Hyderabad", 9, ["Hyderabad", "hyderabad", "Hyd"]),
    ("Chennai", 8, ["Chennai", "Madras", "chennai"]),
    ("Pune", 7, ["Pune", "pune", "Poona"]),
    ("Kolkata", 7, ["Kolkata", "Calcutta", "kolkata"]),
    ("Ahmedabad", 5, ["Ahmedabad", "Amdavad", "ahmedabad"]),
    ("Gurugram", 4, ["Gurugram", "Gurgaon", "gurgaon"]),
    ("Noida", 3, ["Noida", "noida"]),
    ("Jaipur", 3, ["Jaipur", "jaipur"]),
    ("Lucknow", 2, ["Lucknow", "lucknow"]),
    ("Chandigarh", 2, ["Chandigarh", "chandigarh"]),
    ("Kochi", 2, ["Kochi", "Cochin", "kochi"]),
    ("Indore", 2, ["Indore", "indore"]),
    ("Bhopal", 2, ["Bhopal", "bhopal"]),
    ("Surat", 2, ["Surat", "surat"]),
    ("Nagpur", 1, ["Nagpur", "nagpur"]),
    ("Coimbatore", 1, ["Coimbatore", "Kovai", "coimbatore"]),
    ("Visakhapatnam", 1, ["Visakhapatnam", "Vizag", "vizag"]),
]

# category -> refund probability
CATEGORIES = {
    "Electronics": 0.04,
    "Fashion": 0.12,
    "Home & Kitchen": 0.05,
    "Beauty": 0.03,
    "Books": 0.01,
    "Sports": 0.05,
}

PRODUCTS = [  # (id, category, base price in rupees)
    ("P101", "Electronics", 1999),
    ("P102", "Electronics", 2499),
    ("P103", "Electronics", 899),
    ("P104", "Electronics", 3499),
    ("P105", "Electronics", 1299),
    ("P201", "Fashion", 799),
    ("P202", "Fashion", 1499),
    ("P203", "Fashion", 599),
    ("P204", "Fashion", 2199),
    ("P205", "Fashion", 999),
    ("P301", "Home & Kitchen", 1199),
    ("P302", "Home & Kitchen", 649),
    ("P303", "Home & Kitchen", 2899),
    ("P304", "Home & Kitchen", 449),
    ("P401", "Beauty", 349),
    ("P402", "Beauty", 599),
    ("P403", "Beauty", 899),
    ("P404", "Beauty", 249),
    ("P501", "Books", 399),
    ("P502", "Books", 299),
    ("P503", "Books", 549),
    ("P601", "Sports", 1499),
    ("P602", "Sports", 799),
    ("P603", "Sports", 2499),
]

# evening-heavy shopping, as for most Indian e-commerce traffic
HOUR_WEIGHTS = [1, 1, 1, 1, 1, 1, 2, 3, 4, 5, 6, 6, 7, 7, 6, 6, 6, 7, 8, 10, 11, 11, 8, 4]


@cache
def _customers():
    """The fixed customer pool, sorted by signup date, with cumulative weights."""
    city_weights = [w for _, w, _ in CITIES]
    pool = []
    for i in range(1, N_CUSTOMERS + 1):
        rng = random.Random(f"customer-{i}")
        pool.append(
            {
                "id": f"C{i:05d}",
                "signup": EPOCH + timedelta(days=rng.randint(0, 900)),
                "city": rng.choices(CITIES, weights=city_weights)[0],
                "app_user": rng.random() < 0.6,
                "loyalty": min(rng.paretovariate(1.3), 20.0),  # few heavy repeat buyers
            }
        )
    pool.sort(key=lambda c: (c["signup"], c["id"]))
    signups = [c["signup"] for c in pool]
    cum_weights = list(accumulate(c["loyalty"] for c in pool))
    return pool, signups, cum_weights


def _sessions_for(day: date, rng: random.Random, scale: float) -> int:
    growth = 1 + 0.6 * (day - EPOCH).days / 730
    weekend = 1.25 if day.weekday() >= 5 else 1.0
    festive = 1.6 if (day.month, day.day) >= (10, 15) and (day.month, day.day) <= (11, 15) else 1.0
    return max(
        1, round(SESSIONS_PER_DAY * growth * weekend * festive * scale * rng.uniform(0.9, 1.1))
    )


def _fmt_ts(moment: datetime, rng: random.Random) -> str:
    roll = rng.random()
    if roll < 0.70:
        return moment.isoformat(timespec="seconds")  # 2026-03-01T19:04:11+05:30
    if roll < 0.85:
        return moment.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    if roll < 0.95:
        return moment.strftime("%d/%m/%Y %H:%M:%S")  # local time, no zone
    return str(int(moment.timestamp() * 1000))  # epoch milliseconds


def _fmt_price(amount: float, rng: random.Random) -> float | str:
    return f"₹{amount:,.2f}" if rng.random() < 0.2 else amount


def _event_id(*parts) -> str:
    return "evt_" + hashlib.sha1("|".join(map(str, parts)).encode()).hexdigest()[:16]


def _generate_day(day: date, scale: float) -> list[tuple[date, dict]]:
    """All events that happened because of sessions on `day`, with their arrival date."""
    pool, signups, cum_weights = _customers()
    eligible = bisect_right(signups, day)
    if eligible == 0:
        return []
    rng = random.Random(f"day-{day.isoformat()}")
    n_sessions = _sessions_for(day, rng, scale)
    shoppers = rng.choices(pool[:eligible], cum_weights=cum_weights[:eligible], k=n_sessions)

    out: list[tuple[date, dict]] = []

    def emit(moment: datetime, event: dict, may_be_late: bool = True):
        event["ts"] = _fmt_ts(moment, rng)
        late = may_be_late and rng.random() < LATE_SHARE
        out.append((moment.date() + timedelta(days=late), event))
        if rng.random() < 0.01:  # tracker retried: exact duplicate delivery
            out.append((moment.date() + timedelta(days=late), dict(event)))

    for s, customer in enumerate(shoppers):
        session_id = f"S{day:%Y%m%d}{s:05d}"
        city = rng.choice(customer["city"][2])
        channel = "app" if (customer["app_user"] and rng.random() < 0.9) else "web"
        device = "mobile" if channel == "app" or rng.random() < 0.55 else "desktop"
        base = {
            "customer_id": customer["id"],
            "session_id": session_id,
            "city": city,
            "channel": channel,
            "device": device,
        }
        moment = datetime(day.year, day.month, day.day, tzinfo=IST) + timedelta(
            hours=rng.choices(range(24), weights=HOUR_WEIGHTS)[0], minutes=rng.randint(0, 50)
        )
        step = 0

        # Called only inside this loop iteration, so the loop variables are current.
        def next_event(event_type: str, **fields) -> dict:
            nonlocal moment, step
            step += 1
            moment += timedelta(seconds=rng.randint(10, 120))
            return {
                "event_id": _event_id(session_id, step),  # noqa: B023
                "event_type": event_type,
                **base,  # noqa: B023
                **fields,
            }

        product = None
        for _ in range(rng.randint(1, 3)):
            product = rng.choice(PRODUCTS)
            emit(moment, next_event("page_view", product_id=product[0], category=product[1]))
        if rng.random() > 0.15:
            continue
        price = round(product[2] * rng.uniform(0.9, 1.1), 2)
        qty = rng.choices([1, 2, 3], weights=[85, 12, 3])[0]
        item = {"product_id": product[0], "category": product[1], "quantity": qty}
        emit(moment, next_event("add_to_cart", **item, price=_fmt_price(price, rng)))
        if rng.random() > 0.60:
            continue
        emit(moment, next_event("checkout_started", **item, price=_fmt_price(price, rng)))
        if rng.random() > 0.78:
            continue
        order_id = f"ORD-{day:%y%m%d}-{s:05d}"
        order = next_event("order_placed", **item, price=_fmt_price(price, rng), order_id=order_id)
        emit(moment, order)
        if rng.random() < 0.005:  # double-click on "Pay": same order, new event id
            emit(moment + timedelta(seconds=2), {**order, "event_id": _event_id(order_id, "dup")})
        if rng.random() < CATEGORIES[product[1]]:
            refund_at = moment + timedelta(hours=rng.randint(6, 72))
            emit(
                refund_at,
                {
                    "event_id": _event_id(order_id, "refund"),
                    "event_type": "order_refunded",
                    **base,
                    "order_id": order_id,
                },
                may_be_late=False,
            )

    # a few malformed events that the ingest step must quarantine
    for k in range(max(1, n_sessions // 300)):
        broken = {
            "event_id": _event_id(day, "broken", k),
            "event_type": "pageView",
            "customer_id": rng.choice(pool[:eligible])["id"],
            "session_id": f"S{day:%Y%m%d}X",
        }
        if k % 2:
            broken.update(event_type="page_view", customer_id=None)
        emit(datetime(day.year, day.month, day.day, 12, tzinfo=IST), broken, may_be_late=False)
    return out


def generate_batch(start: date, end: date, scale: float = 1.0) -> list[dict]:
    """Events that *arrive* between `start` and `end` (inclusive)."""
    events = []
    day = start - timedelta(days=LOOKBACK_DAYS)
    while day <= end:
        events += [e for arrival, e in _generate_day(day, scale) if start <= arrival <= end]
        day += timedelta(days=1)
    return events
