"""Unit tests for event validation (the quarantine rules). No database needed."""

from pipeline.ingest import payload_hash, validate_event

VALID = {
    "event_id": "evt_1",
    "event_type": "page_view",
    "ts": "2026-03-01T10:00:00+05:30",
    "customer_id": "C00001",
    "session_id": "S1",
    "city": "Pune",
}


def test_valid_event_has_no_error():
    assert validate_event(VALID) is None


def test_extra_fields_are_allowed():
    assert validate_event({**VALID, "utm_source": "instagram"}) is None


def test_missing_customer_is_rejected():
    event = {k: v for k, v in VALID.items() if k != "customer_id"}
    assert "customer_id" in validate_event(event)


def test_blank_customer_is_rejected():
    assert "customer_id" in validate_event({**VALID, "customer_id": ""})


def test_unknown_event_type_is_rejected():
    assert "event_type" in validate_event({**VALID, "event_type": "pageView"})


def test_empty_event_id_is_rejected():
    assert "event_id" in validate_event({**VALID, "event_id": ""})


def test_non_object_payload_is_rejected():
    assert validate_event(["not", "a", "dict"]) is not None


def test_payload_hash_ignores_key_order():
    reordered = dict(reversed(list(VALID.items())))
    assert payload_hash(VALID) == payload_hash(reordered)
    assert payload_hash(VALID) != payload_hash({**VALID, "city": "Surat"})
