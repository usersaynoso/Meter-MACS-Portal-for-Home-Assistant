from __future__ import annotations

import logging
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers import config_validation as cv
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from homeassistant.const import Platform

from .const import (
    DOMAIN,
    PLATFORMS,
    CONF_SCAN_INTERVAL_MINUTES,
    CONF_SELECTED_METERS,
    DEFAULT_SCAN_INTERVAL_MINUTES,
)
from .api import MeterMacsClient
from .coordinator import MeterMacsCoordinator
from .helpers import (
    build_meter_device_key,
    extract_meter_id_from_unique_id,
    selected_meter_ids_from_options,
)

_LOGGER = logging.getLogger(__name__)
CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    session = async_get_clientsession(hass)

    email: str = entry.data.get("email", "")
    password: str = entry.data.get("password", "")

    scan_minutes: int = entry.options.get(
        CONF_SCAN_INTERVAL_MINUTES, DEFAULT_SCAN_INTERVAL_MINUTES
    )
    selected_meter_ids = selected_meter_ids_from_options(entry.options)

    client = MeterMacsClient(session=session, email=email, password=password)

    coordinator = MeterMacsCoordinator(
        hass=hass,
        client=client,
        update_interval=timedelta(minutes=max(2, int(scan_minutes))),
        selected_meter_ids=selected_meter_ids,
    )

    await coordinator.async_config_entry_first_refresh()

    if DOMAIN not in hass.data:
        hass.data[DOMAIN] = {}

    hass.data[DOMAIN][entry.entry_id] = {
        "client": client,
        "coordinator": coordinator,
    }

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    await _async_sync_asset_registries(hass, entry, coordinator)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data.get(DOMAIN, {}).pop(entry.entry_id, None)
    return unload_ok


async def _async_sync_asset_registries(
    hass: HomeAssistant,
    entry: ConfigEntry,
    coordinator: MeterMacsCoordinator,
) -> None:
    discovered_meter_ids = {meter.meter_id for meter in coordinator.all_meters}
    if not discovered_meter_ids:
        return

    selected_meter_ids = selected_meter_ids_from_options(entry.options)
    entity_registry = er.async_get(hass)

    for registry_entry in er.async_entries_for_config_entry(entity_registry, entry.entry_id):
        meter_id = extract_meter_id_from_unique_id(entry.entry_id, registry_entry.unique_id)
        if meter_id is None or meter_id not in discovered_meter_ids:
            continue
        if selected_meter_ids is None or meter_id in selected_meter_ids:
            continue
        entity_registry.async_remove(registry_entry.entity_id)

    valid_device_keys = {
        build_meter_device_key(entry.entry_id, meter_id)
        for meter_id in discovered_meter_ids
        if selected_meter_ids is None or meter_id in selected_meter_ids
    }
    valid_device_keys.add(entry.entry_id)

    device_registry = dr.async_get(hass)
    for device in dr.async_entries_for_config_entry(device_registry, entry.entry_id):
        meter_macs_keys = {
            identifier[1]
            for identifier in device.identifiers
            if len(identifier) >= 2 and identifier[0] == DOMAIN
        }
        if not meter_macs_keys:
            continue
        if meter_macs_keys == {entry.entry_id}:
            device_registry.async_remove_device(device.id)
            continue
        if meter_macs_keys.isdisjoint(valid_device_keys):
            device_registry.async_remove_device(device.id)
