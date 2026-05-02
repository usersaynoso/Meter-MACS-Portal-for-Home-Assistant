# Repository Instructions

- Before every `git commit` or `git push`, bump the integration version in `custom_components/meter_macs/manifest.json`.
- Use semantic versioning and default to a patch bump unless the change clearly requires a minor or major bump.
- Do not leave the repo in a state where code changes are committed or pushed without a matching manifest version bump.
- Every manifest bump that is committed or pushed must also get a matching git tag in the form `vX.Y.Z` from the same version.
- HACS does not treat a manifest bump or pushed tag by itself as a new downloadable version once the repo is using GitHub Releases. Publish or trigger a matching GitHub Release for the same `vX.Y.Z` tag every time, or HACS can keep showing the previous version.
- When asked to bump a GitHub Release, write or update the release message in plain, easy-to-understand language for non-technical users. Avoid jargon, explain what changed and what the user should notice, and include a small touch of humour plus relevant emojis.
- Do not report success after a version bump until all of the following are true: the commit is pushed, the matching `vX.Y.Z` git tag is pushed, and `https://api.github.com/repos/usersaynoso/Meter-MACS-Portal-for-Home-Assistant/releases/latest` returns that same `tag_name`.
- If the latest release API still shows the previous version, keep going and fix the tag/release instead of stopping at the commit or push step.
