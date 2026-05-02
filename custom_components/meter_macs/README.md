# Meter MACS

Home Assistant custom integration for Meter MACS prepaid electricity accounts.

This package:
- Signs in with your Meter MACS portal credentials
- Discovers meters from the portal API when available
- Falls back to dashboard scraping when needed
- Creates balance, imported-energy, balance-updated, last-updated, and cost-per-kWh sensors, plus supply switches where supported
- Creates one Home Assistant device per discovered asset
- Lets you choose which assets stay enabled from integration options

## HACS

Add `https://github.com/usersaynoso/Meter-MACS-Portal-for-Home-Assistant` to HACS as a custom repository of type `Integration`, then install `Meter MACS` from HACS and restart Home Assistant.

## Install

1. Copy `custom_components/meter_macs/` into your Home Assistant `config/custom_components/` directory.
2. Restart Home Assistant.
3. Go to `Settings -> Devices & Services -> Add Integration`.
4. Search for `Meter MACS`.
5. Enter your Meter MACS email address and password.
6. Optionally adjust the refresh interval in integration options.

## Notes

- Default refresh interval: `120` seconds
- Minimum refresh interval: `30` seconds
- Reloading the integration performs an immediate refresh
- Reauthentication is supported through Home Assistant
- The supply switch is optimistic and does not yet confirm the true portal state after a toggle
- The integration depends on Meter MACS portal/API behavior and may require updates if the portal changes
- Brand assets are bundled locally for Home Assistant `2026.3+`

Full repository documentation lives in the root `README.md`.
