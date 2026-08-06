"""Integrity checks for the supplementary fresh-context forward evaluation."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_forward_eval_summary_covers_behavior_suite_without_claiming_release_gate():
    suite = json.loads((ROOT / "evals" / "v2-behavior-evals.json").read_text(encoding="utf-8"))
    result = json.loads(
        (ROOT / "evals" / "results" / "2026-07-11-codex-forward.json").read_text(
            encoding="utf-8"
        )
    )
    expected_ids = {case["id"] for case in suite}
    observed_ids = {case["id"] for case in result["results"]}
    assert observed_ids == expected_ids
    assert len(observed_ids) == result["summary"]["case_count"] == 24
    assert result["summary"]["passed"] == 24
    assert result["summary"]["failed"] == 0
    assert result["summary"]["p0_failures"] == 0
    assert result["summary"]["score_percent"] == 100
    assert result["summary"]["release_gate_satisfied"] is False
    assert result["limitations"]
