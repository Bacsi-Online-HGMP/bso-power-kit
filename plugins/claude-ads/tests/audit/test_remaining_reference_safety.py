"""Regression checks for v2 reference-layer evidence and safety boundaries."""

from __future__ import annotations

import json


AUDIT_SOURCES = {
    "amazon": "amazon-ads-api-official",
    "apple": "apple-ads-api-official",
    "youtube": "youtube-google-ads-video-official",
    "reddit": "reddit-business-help",
    "pinterest": "pinterest-conversions-api",
    "snapchat": "snap-marketing-api",
    "x": "x-conversion-tracking",
}


def test_additional_audits_name_registered_sources_and_runtime_boundary(repo_root):
    ledger = json.loads(
        (repo_root / "control-plane/manifests/source-ledger.json").read_text(
            encoding="utf-8"
        )
    )
    registered = {source["id"] for source in ledger["sources"]}

    for platform, source_id in AUDIT_SOURCES.items():
        text = (repo_root / f"ads/references/{platform}-audit.md").read_text(
            encoding="utf-8"
        )
        assert source_id in registered
        assert f"`{source_id}`" in text
        assert "## Runtime evaluation contract" in text
        assert "`unknown`" in text
        assert "`not_applicable`" in text
        assert "does not provide a live" in text


def test_reference_layer_rejects_legacy_automatic_actions(repo_root):
    references = repo_root / "ads/references"
    text = "\n".join(
        (references / name).read_text(encoding="utf-8")
        for name in (
            "gaql-notes.md",
            "thinking-framework.md",
            "tiktok-creative-specs.md",
            "image-providers.md",
        )
    )
    forbidden = (
        "True intentional broad match is ALWAYS",
        "The 3× Kill Rule",
        "There is no alternative",
        "default image generation provider",
        "auto-uses `gemini",
    )
    for phrase in forbidden:
        assert phrase not in text


def test_creative_guides_require_current_specification_evidence(repo_root):
    for platform in ("google", "meta", "linkedin", "tiktok", "microsoft", "youtube"):
        text = (
            repo_root / f"ads/references/{platform}-creative-specs.md"
        ).read_text(encoding="utf-8")
        normalized = " ".join(text.split())
        assert "## Specification gate" in text
        assert "official source ID" in normalized
        assert "does not imply" in normalized or "no live" in normalized
