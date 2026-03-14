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
DEFAULT_SCAN_INTERVAL_SECONDS = INTERVALS.DEFAULT_SCAN_INTERVAL_SECONDS
LEGACY_CONF_SCAN_INTERVAL_MINUTES = INTERVALS.LEGACY_CONF_SCAN_INTERVAL_MINUTES
MIN_SCAN_INTERVAL_SECONDS = INTERVALS.MIN_SCAN_INTERVAL_SECONDS
resolve_scan_interval_seconds = INTERVALS.resolve_scan_interval_seconds
validate_scan_interval_seconds = INTERVALS.validate_scan_interval_seconds


def test_validate_scan_interval_seconds_accepts_minimum_and_above() -> None:
    assert validate_scan_interval_seconds(MIN_SCAN_INTERVAL_SECONDS) == 30
    assert validate_scan_interval_seconds("120") == 120


def test_validate_scan_interval_seconds_rejects_values_below_minimum() -> None:
    try:
        validate_scan_interval_seconds(29)
    except ValueError as err:
        assert str(err) == "Minimum is 30"
    else:
        raise AssertionError("validate_scan_interval_seconds should reject values below the minimum")


def test_resolve_scan_interval_seconds_defaults_to_new_interval() -> None:
    assert resolve_scan_interval_seconds({}) == DEFAULT_SCAN_INTERVAL_SECONDS


def test_resolve_scan_interval_seconds_prefers_seconds_option() -> None:
    options = {
        CONF_SCAN_INTERVAL_SECONDS: "45",
        LEGACY_CONF_SCAN_INTERVAL_MINUTES: 15,
    }

    assert resolve_scan_interval_seconds(options) == 45


def test_resolve_scan_interval_seconds_converts_legacy_minutes() -> None:
    assert resolve_scan_interval_seconds({LEGACY_CONF_SCAN_INTERVAL_MINUTES: 15}) == 900
