---
name: checking-ha-version-compatibility
description: Fastest way to check whether the integration is ready for a new Home Assistant release
metadata:
  node_type: memory
  type: reference
  originSessionId: 3bb5ba6e-a9c8-45b3-a43d-ac3cb91da674
  modified: 2026-11-09T14:47:12.749Z
---

- HA developer blog moved: `developers.home-assistant.io/blog` 301s to `https://contributors.home-assistant.io/blog/` - fetch that directly. One fetch of the index lists every deprecation with its target version.
- Blog summaries are often vague on whether old patterns still work. Settle it from core source at the release tag: `curl -sL https://raw.githubusercontent.com/home-assistant/core/<version>/homeassistant/<path>` into the scratchpad and grep. That is how the 2026.11 plain-dict `device_info` question was answered (`helpers/entity_platform.py` device lookup).
- From 2026.11 HACS is built into HA as the Marketplace; existing installs migrate automatically and it reads the same `hacs.json` / `zip_release`.

Related: [[running-meter-macs-tests]]
