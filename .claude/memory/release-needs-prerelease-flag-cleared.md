---
name: release-needs-prerelease-flag-cleared
description: commit-and-push script publishes Meter MACS releases as pre-releases; clear the flag or HACS / latest API stays on the old version
metadata:
  node_type: memory
  type: feedback
  originSessionId: 3bb5ba6e-a9c8-45b3-a43d-ac3cb91da674
  modified: 2026-11-09T14:47:04.089Z
---

The shared commit-and-push script (`~/.claude/skills/commit-and-push/scripts/commit-push-release.sh`) always runs `gh release create --prerelease`. In this repo the tag push also fires `.github/workflows/release.yml`, which sees the release already exists and only uploads `meter_macs.zip` - it does not clear the flag. A pre-release is never "latest", so HACS / the HA Marketplace and `releases/latest` keep showing the previous version.

**Why:** AGENTS.md forbids reporting success until `https://api.github.com/repos/usersaynoso/Meter-MACS-Portal-for-Home-Assistant/releases/latest` returns the new tag.

**How to apply:** run the script with `--manifest custom_components/meter_macs/manifest.json` (no package.json here), then in ONE call: `gh release edit vX.Y.Z --repo usersaynoso/Meter-MACS-Portal-for-Home-Assistant --prerelease=false --latest`, confirm the zip asset is attached, and curl `releases/latest` for `tag_name`. The script also refuses https remotes; origin was switched to `git@github.com:usersaynoso/Meter-MACS-Portal-for-Home-Assistant.git` on 2026-11-09 - if it is ever https again, switch it back to ssh rather than fighting the script.

Related: [[running-meter-macs-tests]]
