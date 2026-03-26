from __future__ import annotations

import math
from typing import Mapping


CONF_SCAN_INTERVAL_SECONDS = "scan_interval_seconds"
CONF_SCAN_INTERVAL_MINUTES = "scan_interval_minutes"
LEGACY_CONF_SCAN_INTERVAL_MINUTES = CONF_SCAN_INTERVAL_MINUTES

DEFAULT_SCAN_INTERVAL_SECONDS = 60
MIN_SCAN_INTERVAL_SECONDS = 60
DEFAULT_SCAN_INTERVAL_MINUTES = DEFAULT_SCAN_INTERVAL_SECONDS // 60
MIN_SCAN_INTERVAL_MINUTES = MIN_SCAN_INTERVAL_SECONDS // 60


def validate_scan_interval_seconds(value: object) -> int:
    try:
        seconds = int(value)
    except (TypeError, ValueError) as err:
        raise ValueError("Invalid number") from err

    if seconds < MIN_SCAN_INTERVAL_SECONDS:
        raise ValueError(f"Minimum is {MIN_SCAN_INTERVAL_SECONDS}")
    return seconds


def validate_scan_interval_minutes(value: object) -> int:
    try:
        minutes = int(value)
    except (TypeError, ValueError) as err:
        raise ValueError("Invalid number") from err

    if minutes < MIN_SCAN_INTERVAL_MINUTES:
        raise ValueError(f"Minimum is {MIN_SCAN_INTERVAL_MINUTES}")
    return minutes


def scan_interval_seconds_to_minutes(value: object) -> int:
    seconds = validate_scan_interval_seconds(value)
    return max(MIN_SCAN_INTERVAL_MINUTES, math.ceil(seconds / 60))


def resolve_scan_interval_seconds(options: Mapping[str, object] | None) -> int:
    values = options or {}

    if CONF_SCAN_INTERVAL_MINUTES in values:
        try:
            return validate_scan_interval_minutes(values[CONF_SCAN_INTERVAL_MINUTES]) * 60
        except ValueError:
            return DEFAULT_SCAN_INTERVAL_SECONDS

    if CONF_SCAN_INTERVAL_SECONDS in values:
        try:
            return validate_scan_interval_seconds(values[CONF_SCAN_INTERVAL_SECONDS])
        except ValueError:
            return DEFAULT_SCAN_INTERVAL_SECONDS

    if LEGACY_CONF_SCAN_INTERVAL_MINUTES in values:
        try:
            return max(MIN_SCAN_INTERVAL_SECONDS, int(values[LEGACY_CONF_SCAN_INTERVAL_MINUTES]) * 60)
        except (TypeError, ValueError):
            return DEFAULT_SCAN_INTERVAL_SECONDS

    return DEFAULT_SCAN_INTERVAL_SECONDS
