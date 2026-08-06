"""Structural assertions for the public-safe data lifecycle policy."""

from __future__ import annotations

import json
from pathlib import Path


def test_policy_covers_each_classification_and_required_safeguard(repo_root: Path):
    policy = json.loads(
        (repo_root / "control-plane/manifests/data-lifecycle-policy.json").read_text(encoding="utf-8")
    )
    classes = {entry["id"]: entry for entry in policy["classifications"]}
    assert set(classes) == {"public", "internal", "confidential", "restricted"}
    assert all(entry["minimum_retention_seconds"] == 0 for entry in classes.values())
    assert all(entry["verification_required"] is True for entry in classes.values())
    for classification in ("internal", "confidential", "restricted"):
        assert classes[classification]["encryption_at_rest_required"] is True
        assert classes[classification]["encryption_in_transit_required"] is True
    assert classes["confidential"]["repository_allowed"] is False
    assert classes["restricted"]["repository_allowed"] is False
    assert "legal" not in " ".join(policy["principles"]).lower()


def test_policy_schema_is_strict_and_versioned(repo_root: Path):
    schema = json.loads(
        (repo_root / "control-plane/schemas/data-lifecycle-policy.schema.json").read_text(encoding="utf-8")
    )
    assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    assert schema["additionalProperties"] is False
    assert set(schema["required"]) == set(schema["properties"])
