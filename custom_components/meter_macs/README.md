# Meter MACS – Home Assistant Custom Integration

Fetch balances from the Meter MACS portal and expose them as sensors.

- Source: https://portal.meter-macs.com/dashboard

## Installation
1. Copy `custom_components/meter_macs/` into your Home Assistant `config/custom_components/` folder.
2. Restart Home Assistant.
3. Settings -> Devices & Services -> Add Integration -> Meter MACS.
4. Enter your portal email and password.
5. In integration Options, set the update interval in minutes (min 2).

## Entities
- One balance sensor per meter detected on your dashboard.
- Device class: monetary; unit: currency code when detected (e.g. ZAR).

## Notes
- This integration scrapes HTML. If the portal adds CAPTCHA/MFA or changes markup, parsing may break.
- Credentials are stored in the config entry and never logged.

## Support
Use the Home Assistant logs to diagnose issues. Enable debug logger for `custom_components.meter_macs`.
