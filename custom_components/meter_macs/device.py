from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo

from .const import DOMAIN
from .helpers import build_meter_device_key


def build_meter_device_info(
    entry_id: str,
    meter_id: str,
    display_name: str,
    asset_id: object | None,
) -> DeviceInfo:
    return DeviceInfo(
        identifiers={(DOMAIN, build_meter_device_key(entry_id, meter_id))},
        name=f"Meter MACS {display_name}",
        manufacturer="Meter MACS",
        model="Electricity Asset",
        serial_number=str(asset_id or meter_id),
    )
