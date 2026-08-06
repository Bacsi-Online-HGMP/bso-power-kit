"""Audit-catalog integration checks for the production scoring engine."""

from __future__ import annotations

from claude_ads_core.scoring import SEVERITY_WEIGHTS, score_account


def _control(control_id: str, category: str, severity: str) -> dict:
    return {
        "schema_version": "1.0.0",
        "control_id": control_id,
        "category": category,
        "severity": severity,
        "required_inputs": [],
        "source_ids": ["fixture-source"],
        "maturity": "source-grounded",
        "geographies": ["global"],
        "scoring_behavior": "health",
        "stability": "stable",
    }


def _finding(control_id: str, status: str) -> dict:
    return {
        "schema_version": "1.0.0",
        "control_id": control_id,
        "status": status,
        "evidence": [{"fixture": True}] if status in {"pass", "fail"} else [],
        "confidence": "high" if status in {"pass", "fail"} else "none",
        "observation": "",
        "diagnosis": "",
        "recommendation": "",
    }


def test_catalog_severity_weights_match_production(check_catalog):
    declared = check_catalog["severity_multipliers"]
    production = {name: float(weight) for name, weight in SEVERITY_WEIGHTS.items()}
    assert declared == production


def test_catalog_covers_all_twelve_first_class_platforms(check_catalog):
    assert set(check_catalog["platforms"]) == {
        "google", "meta", "youtube", "linkedin", "tiktok", "microsoft",
        "apple", "amazon", "reddit", "pinterest", "snapchat", "x",
    }


def test_audit_integration_scores_categories_before_category_weights():
    controls = [
        _control("A-critical", "a", "critical"),
        _control("A-medium", "a", "medium"),
        _control("B-high", "b", "high"),
    ]
    findings = [
        _finding("A-critical", "pass"),
        _finding("A-medium", "fail"),
        _finding("B-high", "fail"),
    ]
    result = score_account(controls, findings, {"a": 80, "b": 20})
    assert result.health_score == 66.67
    assert result.evidence_coverage == 100.0


def test_unknown_critical_evidence_blocks_low_coverage_score():
    controls = [
        _control("critical", "tracking", "critical"),
        *[_control(f"medium-{index}", "tracking", "medium") for index in range(5)],
    ]
    findings = [_finding(f"medium-{index}", "pass") for index in range(5)]
    result = score_account(controls, findings, {"tracking": 100})
    assert result.evidence_coverage == 50.0
    assert result.status == "insufficient_evidence"
    assert result.health_score is None
