from __future__ import annotations

import pytest

from claude_ads_core.scoring import SEVERITY_WEIGHTS, ScoringError, score_account, score_portfolio


def control(
    control_id: str,
    category: str,
    severity: str,
    *,
    behavior: str = "health",
    stability: str = "stable",
) -> dict:
    return {
        "schema_version": "1.0.0",
        "control_id": control_id,
        "category": category,
        "severity": severity,
        "required_inputs": [],
        "source_ids": ["source-1"],
        "maturity": "source-grounded",
        "geographies": ["global"],
        "scoring_behavior": behavior,
        "stability": stability,
    }


def finding(control_id: str, status: str) -> dict:
    return {
        "schema_version": "1.0.0",
        "control_id": control_id,
        "status": status,
        "evidence": [{"value": True}] if status in {"pass", "fail"} else [],
        "confidence": "high" if status in {"pass", "fail"} else "none",
        "observation": "",
        "diagnosis": "",
        "recommendation": "",
    }


def test_severity_weights_match_v2_contract():
    assert {key: float(value) for key, value in SEVERITY_WEIGHTS.items()} == {
        "critical": 5.0,
        "high": 3.0,
        "medium": 1.0,
        "informational": 0.0,
    }


def test_scores_within_category_before_applying_category_weight():
    controls = [
        control("A-critical", "a", "critical"),
        control("A-medium", "a", "medium"),
        control("B-high", "b", "high"),
    ]
    findings = [
        finding("A-critical", "pass"),
        finding("A-medium", "fail"),
        finding("B-high", "fail"),
    ]
    result = score_account(controls, findings, {"a": 80, "b": 20})
    assert result.health_score == 66.67
    assert [category.health_score for category in result.categories] == [83.33, 0.0]


def test_unknown_reduces_coverage_without_changing_health_at_80_percent():
    controls = [control(f"C-{index}", "tracking", "high") for index in range(5)]
    findings = [finding(f"C-{index}", "pass") for index in range(4)] + [finding("C-4", "unknown")]
    result = score_account(controls, findings, {"tracking": 100})
    assert result.evidence_coverage == 80.0
    assert result.status == "normal"
    assert result.health_score == 100.0


def test_missing_findings_are_unknown_and_60_percent_is_provisional():
    controls = [control(f"C-{index}", "tracking", "high") for index in range(5)]
    findings = [finding(f"C-{index}", "pass") for index in range(3)]
    result = score_account(controls, findings, {"tracking": 100})
    assert result.evidence_coverage == 60.0
    assert result.status == "provisional"
    assert result.health_score == 100.0
    assert result.categories[0].unknown_controls == 2


def test_evidence_coverage_is_severity_weighted_not_control_counted():
    controls = [control("critical", "tracking", "critical")] + [
        control(f"medium-{index}", "tracking", "medium") for index in range(5)
    ]
    findings = [finding(f"medium-{index}", "pass") for index in range(5)]
    result = score_account(controls, findings, {"tracking": 100})
    # Five of six controls are known, but they represent only 5/(5+5) of the
    # severity-weighted evidence obligation.
    assert result.evidence_coverage == 50.0
    assert result.categories[0].evidence_coverage == 50.0
    assert result.status == "insufficient_evidence"
    assert result.health_score is None


def test_below_60_percent_returns_insufficient_evidence_without_health_score():
    controls = [control(f"C-{index}", "tracking", "high") for index in range(5)]
    findings = [finding("C-0", "pass"), finding("C-1", "fail")]
    result = score_account(controls, findings, {"tracking": 100})
    assert result.evidence_coverage == 40.0
    assert result.status == "insufficient_evidence"
    assert result.health_score is None


def test_not_applicable_is_excluded_from_health_and_coverage():
    controls = [control("known", "tracking", "critical"), control("na", "tracking", "critical")]
    findings = [finding("known", "pass"), finding("na", "not_applicable")]
    result = score_account(controls, findings, {"tracking": 100})
    assert result.health_score == 100.0
    assert result.evidence_coverage == 100.0
    assert result.categories[0].applicable_controls == 1


def test_opportunities_watchlists_and_experimental_controls_are_unscored():
    controls = [
        control("stable", "tracking", "high"),
        control("opportunity", "tracking", "critical", behavior="opportunity"),
        control("experimental", "tracking", "critical", stability="experimental"),
    ]
    findings = [finding("stable", "pass"), finding("opportunity", "fail"), finding("experimental", "fail")]
    result = score_account(controls, findings, {"tracking": 100})
    assert result.health_score == 100.0
    assert result.categories[0].applicable_controls == 1


def test_informational_control_counts_as_known_evidence_but_not_health_weight():
    controls = [control("critical", "tracking", "critical"), control("info", "tracking", "informational")]
    findings = [finding("critical", "pass"), finding("info", "fail")]
    result = score_account(controls, findings, {"tracking": 100})
    assert result.health_score == 100.0
    assert result.evidence_coverage == 100.0


def test_unknown_informational_control_does_not_distort_coverage():
    controls = [control("critical", "tracking", "critical"), control("info", "tracking", "informational")]
    findings = [finding("critical", "pass"), finding("info", "unknown")]
    result = score_account(controls, findings, {"tracking": 100})
    assert result.health_score == 100.0
    assert result.evidence_coverage == 100.0
    assert result.status == "normal"


def test_no_applicable_weight_has_full_coverage_but_no_health_score():
    controls = [control("na", "tracking", "critical")]
    findings = [finding("na", "not_applicable")]
    result = score_account(controls, findings, {"tracking": 100})
    assert result.evidence_coverage == 100.0
    assert result.status == "insufficient_evidence"
    assert result.health_score is None


def test_category_weights_must_sum_exactly_100():
    with pytest.raises(ScoringError, match="sum to exactly 100"):
        score_account([control("C-1", "tracking", "high")], [finding("C-1", "pass")], {"tracking": 99})


def test_category_weights_must_be_finite():
    with pytest.raises(ScoringError, match="finite"):
        score_account(
            [control("C-1", "tracking", "high")],
            [finding("C-1", "pass")],
            {"tracking": float("nan")},
        )


def test_duplicate_and_unknown_control_ids_are_rejected():
    item = control("C-1", "tracking", "high")
    with pytest.raises(ScoringError, match="duplicate control_id"):
        score_account([item, item], [finding("C-1", "pass")], {"tracking": 100})
    with pytest.raises(ScoringError, match="unknown control_id"):
        score_account([item], [finding("other", "pass")], {"tracking": 100})


def test_portfolio_uses_same_window_spend_share():
    window = {"start": "2026-06-01", "end": "2026-06-30"}
    result = score_portfolio(
        [
            {"account_id": "google", "health_score": 80, "spend": 300, "status": "normal", "window": window},
            {"account_id": "meta", "health_score": 50, "spend": 100, "status": "normal", "window": window},
        ]
    )
    assert result.health_score == 72.5
    assert result.status == "normal"
    assert result.weighting == "spend"
    assert [entry.weight for entry in result.accounts] == [75.0, 25.0]


@pytest.mark.parametrize(
    "accounts",
    [
        [
            {"account_id": "google", "health_score": 80, "spend": 300},
            {"account_id": "meta", "health_score": 60, "spend": None},
        ],
        [
            {"account_id": "google", "health_score": 80, "spend": 0},
            {"account_id": "meta", "health_score": 60, "spend": 0},
        ],
    ],
)
def test_portfolio_uses_equal_provisional_weight_when_spend_unavailable(accounts: list[dict]):
    result = score_portfolio(accounts)
    assert result.health_score == 70.0
    assert result.status == "provisional"
    assert result.weighting == "equal_provisional"
    assert [entry.weight for entry in result.accounts] == [50.0, 50.0]


def test_portfolio_uses_equal_provisional_weight_for_mismatched_windows():
    result = score_portfolio(
        [
            {
                "account_id": "google",
                "health_score": 80,
                "spend": 300,
                "window": {"start": "2026-06-01", "end": "2026-06-30"},
            },
            {
                "account_id": "meta",
                "health_score": 60,
                "spend": 100,
                "window": {"start": "2026-05-01", "end": "2026-05-31"},
            },
        ]
    )
    assert result.health_score == 70.0
    assert result.status == "provisional"
    assert result.weighting == "equal_provisional"


def test_portfolio_with_no_scored_accounts_is_insufficient():
    result = score_portfolio([{"account_id": "google", "health_score": None, "spend": 100}])
    assert result.health_score is None
    assert result.status == "insufficient_evidence"
    assert result.weighting == "none"


def test_scoring_is_deterministic_across_input_order():
    controls = [control("A", "one", "critical"), control("B", "two", "medium")]
    findings = [finding("A", "fail"), finding("B", "pass")]
    expected = score_account(controls, findings, {"one": 60, "two": 40}).to_dict()
    actual = score_account(list(reversed(controls)), list(reversed(findings)), {"two": 40, "one": 60}).to_dict()
    assert actual == expected
