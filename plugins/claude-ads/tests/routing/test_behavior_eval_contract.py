"""Contract checks for the forward-model behavior evaluation pack."""

from __future__ import annotations

import json


def test_behavior_eval_pack_is_release_sized_and_well_formed(repo_root, skill_descriptions):
    cases = json.loads(
        (repo_root / "evals" / "v2-behavior-evals.json").read_text(encoding="utf-8")
    )
    assert 20 <= len(cases) <= 50
    ids = [case["id"] for case in cases]
    assert len(ids) == len(set(ids))
    for case in cases:
        assert case["expected_skill"] in skill_descriptions
        assert case["risk"] in {"P0", "P1", "P2", "normal"}
        assert case["comparison"] == "with_skill_vs_baseline"
        assert case["required_behaviors"]
        assert case["forbidden_behaviors"]
        assert not (set(case["required_behaviors"]) & set(case["forbidden_behaviors"]))


def test_behavior_eval_pack_covers_high_risk_surfaces(repo_root):
    cases = json.loads(
        (repo_root / "evals" / "v2-behavior-evals.json").read_text(encoding="utf-8")
    )
    prompts = json.dumps(cases).lower()
    for concept in (
        "approval", "private ip", "oauth", "delete", "attribution",
        "license", "experiment", "customer", "negative keywords",
    ):
        assert concept in prompts
    assert sum(case["risk"] == "P0" for case in cases) >= 6
