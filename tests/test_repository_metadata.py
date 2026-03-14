from __future__ import annotations

import json
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = REPO_ROOT / "custom_components" / "meter_macs" / "manifest.json"
HACS_PATH = REPO_ROOT / "hacs.json"
README_PATH = REPO_ROOT / "README.md"
BRAND_DIR = REPO_ROOT / "custom_components" / "meter_macs" / "brand"
WORKFLOWS_DIR = REPO_ROOT / ".github" / "workflows"
AGENTS_PATH = REPO_ROOT / "AGENTS.md"


def test_hacs_json_exists_and_has_name() -> None:
    data = json.loads(HACS_PATH.read_text(encoding="utf-8"))

    assert data["name"] == "Meter MACS"
    assert data["country"] == "GB"


def test_manifest_has_github_metadata_and_real_codeowner() -> None:
    data = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))

    assert data["documentation"].startswith(
        "https://github.com/usersaynoso/Meter-MACS-Portal-for-Home-Assistant"
    )
    assert data["issue_tracker"].endswith("/issues")
    assert data["codeowners"] == ["@usersaynoso"]
    assert data["version"] == "0.1.19"


def test_manifest_keys_match_hassfest_order() -> None:
    raw = MANIFEST_PATH.read_text(encoding="utf-8")
    data = json.loads(raw)

    assert list(data.keys()) == [
        "domain",
        "name",
        "codeowners",
        "config_flow",
        "documentation",
        "integration_type",
        "iot_class",
        "issue_tracker",
        "loggers",
        "requirements",
        "version",
    ]


def test_local_brand_assets_exist() -> None:
    expected_files = {
        "icon.png",
        "dark_icon.png",
        "logo.png",
        "dark_logo.png",
    }

    assert BRAND_DIR.is_dir()
    assert expected_files.issubset({path.name for path in BRAND_DIR.iterdir()})


def test_hacs_submission_workflows_exist() -> None:
    validate_workflow = WORKFLOWS_DIR / "validate.yml"
    hassfest_workflow = WORKFLOWS_DIR / "hassfest.yml"
    release_workflow = WORKFLOWS_DIR / "release.yml"
    validate_text = validate_workflow.read_text(encoding="utf-8")
    hassfest_text = hassfest_workflow.read_text(encoding="utf-8")
    release_text = release_workflow.read_text(encoding="utf-8")

    assert validate_workflow.is_file()
    assert hassfest_workflow.is_file()
    assert release_workflow.is_file()
    assert "hacs/action@main" in validate_text
    assert "category: integration" in validate_text
    assert "actions/checkout@v6" in hassfest_text
    assert "docker/login-action@v3" in hassfest_text
    assert "packages: read" in hassfest_text
    assert "username: ${{ github.actor }}" in hassfest_text
    assert "password: ${{ secrets.GITHUB_TOKEN }}" in hassfest_text
    assert "HASSFEST_IMAGE: ghcr.io/home-assistant/hassfest@sha256:" in hassfest_text
    assert "for attempt in 1 2 3 4 5;" in hassfest_text
    assert 'docker pull "$HASSFEST_IMAGE"' in hassfest_text
    assert 'docker run --rm -v "$GITHUB_WORKSPACE:/github/workspace" "$HASSFEST_IMAGE"' in hassfest_text
    assert "branches:" in validate_text
    assert "branches:" in hassfest_text
    assert "- main" in validate_text
    assert "- main" in hassfest_text
    assert 'tags:' in release_text
    assert '- "v*"' in release_text
    assert "contents: write" in release_text
    assert "softprops/action-gh-release@v2" in release_text
    assert "generate_release_notes: true" in release_text
    assert "make_latest: true" in release_text


def test_readme_contains_image_for_hacs_rendering() -> None:
    text = README_PATH.read_text(encoding="utf-8")

    assert "![Meter MACS logo]" in text
    assert "custom_components/meter_macs/brand/logo.png" in text


def test_agents_file_requires_manifest_version_bumps() -> None:
    text = AGENTS_PATH.read_text(encoding="utf-8")

    assert AGENTS_PATH.is_file()
    assert "manifest.json" in text
    assert "git commit" in text
    assert "git push" in text
    assert "git tag" in text
    assert "vX.Y.Z" in text
    assert "bump" in text.lower()
    assert "GitHub Release" in text
    assert "releases/latest" in text
    assert "Do not report success" in text
