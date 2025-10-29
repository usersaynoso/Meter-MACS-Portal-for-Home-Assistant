from __future__ import annotations

import logging
from typing import Any, Dict, Optional

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import (
    DOMAIN,
    CONF_SCAN_INTERVAL_MINUTES,
    DEFAULT_SCAN_INTERVAL_MINUTES,
    MIN_SCAN_INTERVAL_MINUTES,
)
from .api import MeterMacsClient, AuthError

_LOGGER = logging.getLogger(__name__)


def _validate_interval(value: int) -> int:
    try:
        v = int(value)
    except Exception:  # noqa: BLE001
        raise vol.Invalid("Invalid number")
    if v < MIN_SCAN_INTERVAL_MINUTES:
        raise vol.Invalid(f"Minimum is {MIN_SCAN_INTERVAL_MINUTES}")
    return v


class MeterMacsConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    def __init__(self) -> None:
        self._email: Optional[str] = None
        self._password: Optional[str] = None

    async def async_step_user(self, user_input: Optional[Dict[str, Any]] = None) -> FlowResult:
        errors: Dict[str, str] = {}

        if user_input is not None:
            email = user_input.get("email", "")
            password = user_input.get("password", "")

            # Use email as unique id
            await self.async_set_unique_id(email)
            self._abort_if_unique_id_configured()

            session = async_get_clientsession(self.hass)
            client = MeterMacsClient(session=session, email=email, password=password)
            try:
                # Validate credentials
                await client.ensure_logged_in()
            except AuthError:
                errors["base"] = "invalid_auth"
            except Exception:  # noqa: BLE001
                errors["base"] = "cannot_connect"
            else:
                return self.async_create_entry(title="Meter MACS", data={"email": email, "password": password})

        data_schema = vol.Schema({
            vol.Required("email", default=(user_input or {}).get("email", "")): str,
            vol.Required("password", default=(user_input or {}).get("password", "")): str,
        })

        return self.async_show_form(step_id="user", data_schema=data_schema, errors=errors)

    async def async_step_reauth(self, entry_data: Dict[str, Any]) -> FlowResult:
        self._email = entry_data.get("email")
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(self, user_input: Optional[Dict[str, Any]] = None) -> FlowResult:
        errors: Dict[str, str] = {}

        if user_input is not None:
            password = user_input.get("password", "")
            session = async_get_clientsession(self.hass)
            client = MeterMacsClient(session=session, email=self._email or "", password=password)
            try:
                await client.ensure_logged_in()
            except AuthError:
                errors["base"] = "invalid_auth"
            except Exception:  # noqa: BLE001
                errors["base"] = "cannot_connect"
            else:
                # Update existing entry with new password
                current = self._get_reauth_entry()
                if isinstance(current, ConfigEntry):
                    new_data = {"email": self._email or "", "password": password}
                    self.hass.config_entries.async_update_entry(current, data=new_data)
                    await self.hass.config_entries.async_reload(current.entry_id)
                return self.async_abort(reason="reauth_successful")

        data_schema = vol.Schema({
            vol.Required("password"): str,
        })
        return self.async_show_form(step_id="reauth_confirm", data_schema=data_schema, errors=errors)


class MeterMacsOptionsFlowHandler(config_entries.OptionsFlow):
    def __init__(self, config_entry: ConfigEntry) -> None:
        self.config_entry = config_entry

    async def async_step_init(self, user_input: Optional[Dict[str, Any]] = None) -> FlowResult:
        errors: Dict[str, str] = {}
        if user_input is not None:
            try:
                minutes = _validate_interval(user_input[CONF_SCAN_INTERVAL_MINUTES])
            except vol.Invalid:
                errors["base"] = "invalid_interval"
            else:
                return self.async_create_entry(title="Options", data={CONF_SCAN_INTERVAL_MINUTES: minutes})

        minutes = self.config_entry.options.get(CONF_SCAN_INTERVAL_MINUTES, DEFAULT_SCAN_INTERVAL_MINUTES)
        data_schema = vol.Schema({
            vol.Required(CONF_SCAN_INTERVAL_MINUTES, default=minutes): int,
        })
        return self.async_show_form(step_id="init", data_schema=data_schema, errors=errors)


async def async_get_options_flow(config_entry: ConfigEntry) -> MeterMacsOptionsFlowHandler:
    return MeterMacsOptionsFlowHandler(config_entry)


