"""Deterministic account-health and portfolio scoring."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Mapping, Sequence

from .contracts import ContractError, validate_contract

SEVERITY_WEIGHTS: Mapping[str, Decimal] = {
    "critical": Decimal("5"),
    "high": Decimal("3"),
    "medium": Decimal("1"),
    "informational": Decimal("0"),
}
CATEGORY_WEIGHT_TOTAL = Decimal("100")
NORMAL_COVERAGE = Decimal("80")
PROVISIONAL_COVERAGE = Decimal("60")


class ScoringError(ValueError):
    """Raised for invalid or internally inconsistent scoring inputs."""


def _decimal(value: Any, field: str) -> Decimal:
    if isinstance(value, bool):
        raise ScoringError(f"{field} must be numeric")
    try:
        result = Decimal(str(value))
    except Exception as exc:
        raise ScoringError(f"{field} must be numeric") from exc
    if not result.is_finite():
        raise ScoringError(f"{field} must be finite")
    return result


def _rounded(value: Decimal) -> float:
    return float(value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


@dataclass(frozen=True)
class CategoryScore:
    category: str
    category_weight: float
    health_score: float | None
    evidence_coverage: float
    applicable_controls: int
    known_controls: int
    passed_controls: int
    failed_controls: int
    unknown_controls: int

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ScoreResult:
    health_score: float | None
    evidence_coverage: float
    status: str
    categories: tuple[CategoryScore, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "health_score": self.health_score,
            "evidence_coverage": self.evidence_coverage,
            "status": self.status,
            "categories": [category.to_dict() for category in self.categories],
        }


@dataclass(frozen=True)
class PortfolioEntry:
    account_id: str
    health_score: float
    weight: float
    spend: float | None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class PortfolioResult:
    health_score: float | None
    status: str
    weighting: str
    accounts: tuple[PortfolioEntry, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "health_score": self.health_score,
            "status": self.status,
            "weighting": self.weighting,
            "accounts": [account.to_dict() for account in self.accounts],
        }


def _coverage_status(coverage: Decimal) -> str:
    if coverage >= NORMAL_COVERAGE:
        return "normal"
    if coverage >= PROVISIONAL_COVERAGE:
        return "provisional"
    return "insufficient_evidence"


def _validated_weights(category_weights: Mapping[str, Any]) -> dict[str, Decimal]:
    if not category_weights:
        raise ScoringError("category_weights must not be empty")
    weights: dict[str, Decimal] = {}
    for category, raw_weight in sorted(category_weights.items()):
        if not isinstance(category, str) or not category:
            raise ScoringError("category weight keys must be non-empty strings")
        weight = _decimal(raw_weight, f"category_weights.{category}")
        if weight < 0:
            raise ScoringError(f"category_weights.{category} must be >= 0")
        weights[category] = weight
    if sum(weights.values(), Decimal("0")) != CATEGORY_WEIGHT_TOTAL:
        raise ScoringError("category weights must sum to exactly 100")
    return weights


def score_account(
    controls: Sequence[Mapping[str, Any]],
    findings: Sequence[Mapping[str, Any]],
    category_weights: Mapping[str, Any],
) -> ScoreResult:
    """Score stable health controls using category-then-portfolio weighting.

    Missing findings are treated as unknown.  Unknown controls reduce
    severity-weighted evidence coverage but never change the health numerator
    or denominator.  Informational controls have zero weight and cannot distort
    coverage.  Controls marked not applicable are removed from both health and
    coverage.
    """

    weights = _validated_weights(category_weights)
    controls_by_id: dict[str, Mapping[str, Any]] = {}
    for control in controls:
        try:
            validate_contract("control-definition", control)
        except ContractError as exc:
            raise ScoringError(str(exc)) from exc
        control_id = str(control["control_id"])
        if control_id in controls_by_id:
            raise ScoringError(f"duplicate control_id: {control_id}")
        controls_by_id[control_id] = control
        if control["category"] not in weights:
            raise ScoringError(f"control {control_id} uses unweighted category {control['category']!r}")

    findings_by_id: dict[str, Mapping[str, Any]] = {}
    for finding in findings:
        try:
            validate_contract("finding", finding)
        except ContractError as exc:
            raise ScoringError(str(exc)) from exc
        control_id = str(finding["control_id"])
        if control_id not in controls_by_id:
            raise ScoringError(f"finding references unknown control_id: {control_id}")
        if control_id in findings_by_id:
            raise ScoringError(f"duplicate finding for control_id: {control_id}")
        findings_by_id[control_id] = finding

    eligible = [
        control
        for control in controls_by_id.values()
        if control["scoring_behavior"] == "health" and control["stability"] == "stable"
    ]
    categories: list[CategoryScore] = []
    raw_category_health: dict[str, Decimal] = {}
    total_applicable_weight = Decimal("0")
    total_known_weight = Decimal("0")

    for category, category_weight in sorted(weights.items()):
        category_controls = [control for control in eligible if control["category"] == category]
        applicable: list[tuple[Mapping[str, Any], str]] = []
        for control in category_controls:
            finding = findings_by_id.get(str(control["control_id"]))
            status = str(finding["status"]) if finding else "unknown"
            if status != "not_applicable":
                applicable.append((control, status))

        known = [(control, status) for control, status in applicable if status in {"pass", "fail"}]
        passed = [(control, status) for control, status in known if status == "pass"]
        failed = [(control, status) for control, status in known if status == "fail"]
        unknown_count = len(applicable) - len(known)
        applicable_weight = sum(
            (SEVERITY_WEIGHTS[str(control["severity"])] for control, _ in applicable),
            Decimal("0"),
        )
        known_weight = sum(
            (SEVERITY_WEIGHTS[str(control["severity"])] for control, _ in known),
            Decimal("0"),
        )
        total_applicable_weight += applicable_weight
        total_known_weight += known_weight

        possible = sum((SEVERITY_WEIGHTS[str(control["severity"])] for control, _ in known), Decimal("0"))
        earned = sum((SEVERITY_WEIGHTS[str(control["severity"])] for control, _ in passed), Decimal("0"))
        raw_health = None if possible == 0 else (earned / possible) * Decimal("100")
        category_health = None if raw_health is None else _rounded(raw_health)
        if raw_health is not None:
            raw_category_health[category] = raw_health
        category_coverage = (
            Decimal("100")
            if applicable_weight == 0
            else known_weight / applicable_weight * Decimal("100")
        )
        categories.append(
            CategoryScore(
                category=category,
                category_weight=_rounded(category_weight),
                health_score=category_health,
                evidence_coverage=_rounded(category_coverage),
                applicable_controls=len(applicable),
                known_controls=len(known),
                passed_controls=len(passed),
                failed_controls=len(failed),
                unknown_controls=unknown_count,
            )
        )

    coverage = (
        Decimal("100")
        if total_applicable_weight == 0
        else total_known_weight / total_applicable_weight * Decimal("100")
    )
    # An audit with no applicable, non-informational health control cannot
    # produce health, even though it has no missing evidence obligation.
    status = "insufficient_evidence" if total_applicable_weight == 0 else _coverage_status(coverage)
    scored_categories = [category for category in categories if category.health_score is not None and category.category_weight > 0]
    active_weight = sum((weights[category.category] for category in scored_categories), Decimal("0"))
    health: float | None = None
    if status != "insufficient_evidence" and active_weight > 0:
        weighted = sum(raw_category_health[category.category] * weights[category.category] for category in scored_categories)
        health = _rounded(weighted / active_weight)
    return ScoreResult(
        health_score=health,
        evidence_coverage=_rounded(coverage),
        status=status,
        categories=tuple(categories),
    )


def score_portfolio(accounts: Sequence[Mapping[str, Any]]) -> PortfolioResult:
    """Aggregate account health using same-window spend or provisional equality.

    Each item requires ``account_id`` and ``health_score``; ``spend`` may be a
    non-negative number or null, and ``window`` contains comparable ``start``
    and ``end`` strings. Accounts without a health score are excluded. If any
    included spend/window is unavailable, windows differ, or total spend is
    zero, equal weights are used and the aggregate is explicitly provisional.
    """

    included: list[tuple[str, Decimal, Decimal | None, str, tuple[str, str] | None]] = []
    for index, account in enumerate(accounts):
        if not isinstance(account, Mapping):
            raise ScoringError(f"accounts[{index}] must be an object")
        account_id = account.get("account_id")
        if not isinstance(account_id, str) or not account_id:
            raise ScoringError(f"accounts[{index}].account_id must be a non-empty string")
        if account.get("health_score") is None:
            continue
        health = _decimal(account["health_score"], f"accounts[{index}].health_score")
        if not Decimal("0") <= health <= Decimal("100"):
            raise ScoringError(f"accounts[{index}].health_score must be between 0 and 100")
        raw_spend = account.get("spend")
        spend = None if raw_spend is None else _decimal(raw_spend, f"accounts[{index}].spend")
        if spend is not None and spend < 0:
            raise ScoringError(f"accounts[{index}].spend must be >= 0")
        status = str(account.get("status", "normal"))
        if status not in {"normal", "provisional", "insufficient_evidence"}:
            raise ScoringError(f"accounts[{index}].status is invalid")
        raw_window = account.get("window")
        window: tuple[str, str] | None = None
        if raw_window is not None:
            if not isinstance(raw_window, Mapping):
                raise ScoringError(f"accounts[{index}].window must be an object")
            start, end = raw_window.get("start"), raw_window.get("end")
            if not isinstance(start, str) or not start or not isinstance(end, str) or not end:
                raise ScoringError(f"accounts[{index}].window requires non-empty start and end strings")
            window = (start, end)
        included.append((account_id, health, spend, status, window))

    if not included:
        return PortfolioResult(None, "insufficient_evidence", "none", ())

    spend_available = all(spend is not None for _, _, spend, _, _ in included)
    windows = [window for _, _, _, _, window in included]
    same_window = all(window is not None for window in windows) and len(set(windows)) == 1
    total_spend = sum((spend or Decimal("0") for _, _, spend, _, _ in included), Decimal("0"))
    if spend_available and same_window and total_spend > 0:
        weighting = "spend"
        raw_weights = [(spend or Decimal("0")) / total_spend for _, _, spend, _, _ in included]
    else:
        weighting = "equal_provisional"
        equal = Decimal("1") / Decimal(len(included))
        raw_weights = [equal for _ in included]

    aggregate = sum((health * weight for (_, health, _, _, _), weight in zip(included, raw_weights)), Decimal("0"))
    entries = tuple(
        PortfolioEntry(
            account_id=account_id,
            health_score=_rounded(health),
            weight=_rounded(weight * Decimal("100")),
            spend=None if spend is None else _rounded(spend),
        )
        for (account_id, health, spend, _, _), weight in zip(included, raw_weights)
    )
    statuses = {status for _, _, _, status, _ in included}
    status = "normal" if weighting == "spend" and statuses == {"normal"} else "provisional"
    return PortfolioResult(_rounded(aggregate), status, weighting, entries)
