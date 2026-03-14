from __future__ import annotations

from homeassistant.const import Platform

from .intervals import (
    CONF_SCAN_INTERVAL_SECONDS,
    DEFAULT_SCAN_INTERVAL_SECONDS,
    LEGACY_CONF_SCAN_INTERVAL_MINUTES,
    MIN_SCAN_INTERVAL_SECONDS,
)

DOMAIN = "meter_macs"

CONF_SELECTED_METERS = "selected_meters"

PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.SWITCH]

BASE_URL = "https://portal.meter-macs.com"
