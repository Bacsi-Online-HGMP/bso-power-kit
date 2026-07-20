#!/usr/bin/env python3
"""Build the .mcpb extension package for Claude Desktop.

Reads version from pyproject.toml, syncs it into desktop-extension/manifest.json,
then packages everything into notebooklm-mcp.mcpb (a zip file).

Usage:
    python scripts/build_mcpb.py
    # or: uv run scripts/build_mcpb.py
"""

import json
import zipfile
from pathlib import Path

# Paths relative to project root
PROJECT_ROOT = Path(__file__).parent.parent
PYPROJECT = PROJECT_ROOT / "pyproject.toml"
MANIFEST = PROJECT_ROOT / "desktop-extension" / "manifest.json"


def get_version_from_pyproject() -> str:
    """Extract version string from pyproject.toml without external deps."""
    text = PYPROJECT.read_text()
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("version") and "=" in stripped:
            # version = "0.2.18"
            return stripped.split("=", 1)[1].strip().strip('"').strip("'")
    raise ValueError("Could not find version in pyproject.toml")


def sync_manifest_version(version: str) -> dict:
    """Update manifest.json with the current version, return the manifest dict."""
    manifest = json.loads(MANIFEST.read_text())
    old_version = manifest.get("version", "unknown")

    if old_version != version:
        manifest["version"] = version
        MANIFEST.write_text(json.dumps(manifest, indent=2) + "\n")
        print(f"  manifest.json: {old_version} → {version}")
    else:
        print(f"  manifest.json: already at {version}")

    return manifest


def build_mcpb() -> None:
    """Build the .mcpb file (zip containing manifest.json)."""
    version = get_version_from_pyproject()
    output = PROJECT_ROOT / f"notebooklm-mcp-{version}.mcpb"

    print(f"\n📦 Building notebooklm-mcp-{version}.mcpb\n")

    # Sync version
    sync_manifest_version(version)

    # Clean up old .mcpb files
    for old in PROJECT_ROOT.glob("notebooklm-mcp*.mcpb"):
        if old != output:
            old.unlink()
            print(f"  🗑  Removed old: {old.name}")

    # Package as zip
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.write(MANIFEST, "manifest.json")
        launcher = PROJECT_ROOT / "desktop-extension" / "run_server.py"
        zf.write(launcher, "run_server.py")

    size_kb = output.stat().st_size / 1024
    print(f"\n✅ Built: {output.name} ({size_kb:.1f} KB)")
    print(f"   Location: {output}")


if __name__ == "__main__":
    build_mcpb()
