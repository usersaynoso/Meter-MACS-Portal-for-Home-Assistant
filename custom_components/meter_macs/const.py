from __future__ import annotations

from homeassistant.const import Platform

DOMAIN = "meter_macs"

CONF_SCAN_INTERVAL_MINUTES = "scan_interval_minutes"
CONF_SELECTED_METERS = "selected_meters"
DEFAULT_SCAN_INTERVAL_MINUTES = 15
MIN_SCAN_INTERVAL_MINUTES = 2

PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.SWITCH]

BASE_URL = "https://portal.meter-macs.com"

