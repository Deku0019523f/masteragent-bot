"""tests/test_helpers.py — duration parsing/formatting helpers."""
from utils.helpers import parse_duration, format_duration


def test_parse_duration_minutes():
    assert parse_duration("10m") == 600


def test_parse_duration_hours():
    assert parse_duration("2h") == 7200


def test_parse_duration_days():
    assert parse_duration("1d") == 86400


def test_parse_duration_invalid():
    assert parse_duration("abc") is None
    assert parse_duration("10") is None


def test_format_duration_roundtrip():
    assert format_duration(600) == "10m"
    assert format_duration(3600) == "1h"
    assert format_duration(86400) == "1j"
