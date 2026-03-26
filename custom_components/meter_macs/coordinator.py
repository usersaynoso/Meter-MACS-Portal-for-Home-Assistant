from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import List

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    UpdateFailed,
)
from homeassistant.exceptions import ConfigEntryAuthFailed

from .api import MeterMacsClient, MeterApi, parse_dashboard_for_meters, AuthError, Meter
from .const import DOMAIN
from .helpers import filter_meter_ids

_LOGGER = logging.getLogger(__name__)


class MeterMacsCoordinator(DataUpdateCoordinator[List[Meter]]):
    def __init__(
        self,
        hass: HomeAssistant,
        client: MeterMacsClient,
        update_interval: timedelta,
        selected_meter_ids: set[str] | None = None,
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=update_interval,
        )
        self._client = client
        self._api = MeterApi(client)
        self._selected_meter_ids = selected_meter_ids
        self.all_meters: List[Meter] = []
        self.last_refresh_time: datetime | None = None

    async def _async_update_data(self) -> List[Meter]:
        try:
            # Prefer JSON API if available
            try:
                meters = await self._api.fetch_meters()
            except Exception:
                # Fallback to HTML parsing if API is not available
                html = await self._client.fetch_dashboard()
                meters = parse_dashboard_for_meters(html)
            self.all_meters = meters
            if self._selected_meter_ids is not None:
                selected_ids = set(
                    filter_meter_ids(
                        (meter.meter_id for meter in meters),
                        self._selected_meter_ids,
                    )
                )
                meters = [meter for meter in meters if meter.meter_id in selected_ids]
            if not meters:
                _LOGGER.debug("No meters parsed from dashboard HTML")
            self.last_refresh_time = datetime.now(timezone.utc)
            return meters
        except AuthError as err:
            raise ConfigEntryAuthFailed from err
        except Exception as err:  # noqa: BLE001
            raise UpdateFailed(str(err)) from err
