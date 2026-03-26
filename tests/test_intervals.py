from __future__ import annotations

import importlib.util
from pathlib import Path


INTERVALS_PATH = (
    Path(__file__).resolve().parents[1]
    / "custom_components"
    / "meter_macs"
    / "intervals.py"
)
SPEC = importlib.util.spec_from_file_location("meter_macs_intervals", INTERVALS_PATH)
INTERVALS = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(INTERVALS)

CONF_SCAN_INTERVAL_SECONDS = INTERVALS.CONF_SCAN_INTERVAL_SECONDS
CONF_SCAN_INTERVAL_MINUTES = INTERVALS.CONF_SCAN_INTERVAL_MINUTES
DEFAULT_SCAN_INTERVAL_SECONDS = INTERVALS.DEFAULT_SCAN_INTERVAL_SECONDS
DEFAULT_SCAN_INTERVAL_MINUTES = INTERVALS.DEFAULT_SCAN_INTERVAL_MINUTES
LEGACY_CONF_SCAN_INTERVAL_MINUTES = INTERVALS.LEGACY_CONF_SCAN_INTERVAL_MINUTES
MIN_SCAN_INTERVAL_SECONDS = INTERVALS.MIN_SCAN_INTERVAL_SECONDS
MIN_SCAN_INTERVAL_MINUTES = INTERVALS.MIN_SCAN_INTERVAL_MINUTES
resolve_scan_interval_seconds = INTERVALS.resolve_scan_interval_seconds
scan_interval_seconds_to_minutes = INTERVALS.scan_interval_seconds_to_minutes
validate_scan_interval_minutes = INTERVALS.validate_scan_interval_minutes
validate_scan_interval_seconds = INTERVALS.validate_scan_interval_seconds


def test_validate_scan_interval_seconds_accepts_minimum_and_above() -> None:
    assert validate_scan_interval_seconds(MIN_SCAN_INTERVAL_SECONDS) == 60
    assert validate_scan_interval_seconds("120") == 120


def test_validate_scan_interval_seconds_rejects_values_below_minimum() -> None:
    try:
        validate_scan_interval_seconds(59)
    except ValueError as err:
        assert str(err) == "Minimum is 60"
    else:
        raise AssertionError("validate_scan_interval_seconds should reject values below the minimum")


def test_validate_scan_interval_minutes_accepts_minimum_and_above() -> None:
    assert validate_scan_interval_minutes(MIN_SCAN_INTERVAL_MINUTES) == 1
    assert validate_scan_interval_minutes("5") == 5


def test_validate_scan_interval_minutes_rejects_values_below_minimum() -> None:
    try:
        validate_scan_interval_minutes(0)
    except ValueError as err:
        assert str(err) == "Minimum is 1"
    else:
        raise AssertionError("validate_scan_interval_minutes should reject values below the minimum")


def test_resolve_scan_interval_seconds_defaults_to_new_interval() -> None:
    assert resolve_scan_interval_seconds({}) == DEFAULT_SCAN_INTERVAL_SECONDS


def test_resolve_scan_interval_seconds_prefers_minutes_option() -> None:
    options = {
        CONF_SCAN_INTERVAL_MINUTES: "5",
        CONF_SCAN_INTERVAL_SECONDS: "120",
    }

    assert resolve_scan_interval_seconds(options) == 300


def test_resolve_scan_interval_seconds_uses_compatible_seconds_option() -> None:
    options = {
        CONF_SCAN_INTERVAL_SECONDS: "120",
    }

    assert resolve_scan_interval_seconds(options) == 120


def test_scan_interval_seconds_to_minutes_rounds_up() -> None:
    assert scan_interval_seconds_to_minutes(60) == DEFAULT_SCAN_INTERVAL_MINUTES
    assert scan_interval_seconds_to_minutes(90) == 2


def test_resolve_scan_interval_seconds_converts_legacy_minutes() -> None:
    assert resolve_scan_interval_seconds({LEGACY_CONF_SCAN_INTERVAL_MINUTES: 15}) == 900
