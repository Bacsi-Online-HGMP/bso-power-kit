"""Deterministic normalization for the portable Claude Ads CSV export format."""

from __future__ import annotations

import csv
import math
from collections import Counter
from datetime import date
from decimal import Decimal, InvalidOperation
from os import PathLike
from pathlib import Path
from typing import Any, Mapping

from ..contracts import PLATFORMS, ContractError, validate_contract
from ..models import AccountSnapshot
from .base import AdapterCapabilities, AdapterError, BaseAdapter, Capability

REQUIRED_COLUMNS = (
    "date",
    "account_id",
    "account_name",
    "campaign_id",
    "campaign_name",
    "campaign_status",
    "creative_id",
    "creative_name",
    "conversion_action",
    "conversions",
    "budget",
    "spend",
    "currency",
)
MAX_EXPORT_BYTES = 50 * 1024 * 1024
MAX_EXPORT_ROWS = 500_000
MAX_EXPORT_COLUMNS = 128


class CSVExportError(AdapterError):
    """Raised when an export cannot be safely and deterministically normalized."""


def _required(row: Mapping[str, str | None], field: str, row_number: int) -> str:
    value = row.get(field)
    if value is None or not value.strip():
        raise CSVExportError(f"row {row_number}: {field} must not be empty")
    return value.strip()


def _date(value: str, field: str, row_number: int) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise CSVExportError(f"row {row_number}: {field} must be an ISO 8601 date") from exc


def _decimal(value: str, field: str, row_number: int) -> Decimal:
    try:
        number = Decimal(value)
    except InvalidOperation as exc:
        raise CSVExportError(f"row {row_number}: {field} must be numeric") from exc
    if not number.is_finite() or number < 0:
        raise CSVExportError(f"row {row_number}: {field} must be a finite non-negative number")
    return number


def _number(value: Decimal) -> float:
    number = float(value)
    if not math.isfinite(number):
        raise CSVExportError("numeric value is outside the supported finite range")
    return number


class GenericCSVExportAdapter(BaseAdapter):
    """Normalize a documented common CSV shape for any target platform.

    This is an export adapter, not a platform API client. Platform-specific
    exports must first map their headers to :data:`REQUIRED_COLUMNS`. Each row
    is one additive daily observation at the unique
    ``(date, campaign_id, creative_id)`` grain. ``spend`` and ``conversions``
    must already be allocated to that grain; repeated grains are rejected
    instead of silently double-counted.
    """

    def __init__(self, platform: str) -> None:
        normalized = platform.strip().lower()
        if normalized not in PLATFORMS:
            raise CSVExportError(f"unsupported platform: {platform!r}")
        self.platform = normalized
        self.adapter_id = f"{normalized}-generic-csv-v1"

    def discover_capabilities(self) -> AdapterCapabilities:
        return AdapterCapabilities(
            schema_version="1.0.0",
            adapter_id=self.adapter_id,
            platform=self.platform,
            default_mutation_mode="read-only",
            capabilities=(
                Capability("normalized-export", "export-read", "fixture-verified"),
                Capability(
                    "account-mutation",
                    "live-write",
                    "disabled",
                    "Generic exports have no authenticated write destination.",
                ),
            ),
        )

    def read_snapshot(self, source: str | PathLike[str]) -> AccountSnapshot:
        path = Path(source)
        try:
            if not path.is_file():
                raise CSVExportError(f"export is not a regular file: {path}")
            size = path.stat().st_size
        except OSError as exc:
            raise CSVExportError(f"cannot inspect export: {exc}") from exc
        if size > MAX_EXPORT_BYTES:
            raise CSVExportError(f"export exceeds {MAX_EXPORT_BYTES} byte limit")

        try:
            with path.open("r", encoding="utf-8-sig", newline="") as handle:
                reader = csv.DictReader(handle, strict=True)
                headers = reader.fieldnames or []
                if len(headers) > MAX_EXPORT_COLUMNS:
                    raise CSVExportError(f"export exceeds {MAX_EXPORT_COLUMNS} column limit")
                duplicates = sorted(field for field, count in Counter(headers).items() if count > 1)
                if duplicates:
                    raise CSVExportError(f"export contains duplicate column(s): {', '.join(duplicates)}")
                missing = [field for field in REQUIRED_COLUMNS if field not in headers]
                if missing:
                    raise CSVExportError(f"export missing required column(s): {', '.join(missing)}")
                rows = []
                for row_number, row in enumerate(reader, start=2):
                    if row_number - 1 > MAX_EXPORT_ROWS:
                        raise CSVExportError(f"export exceeds {MAX_EXPORT_ROWS} row limit")
                    rows.append(self._normalize_row(row, row_number))
        except (OSError, UnicodeError, csv.Error) as exc:
            raise CSVExportError(f"cannot read export: {exc}") from exc
        if not rows:
            raise CSVExportError("export must contain at least one data row")
        return self._build_snapshot(rows)

    def _normalize_row(self, row: Mapping[str, str | None], row_number: int) -> dict[str, Any]:
        normalized = {field: _required(row, field, row_number) for field in REQUIRED_COLUMNS}
        normalized["date"] = _date(normalized["date"], "date", row_number)
        normalized["conversions"] = _decimal(normalized["conversions"], "conversions", row_number)
        normalized["budget"] = _decimal(normalized["budget"], "budget", row_number)
        normalized["spend"] = _decimal(normalized["spend"], "spend", row_number)
        currency = normalized["currency"]
        if len(currency) != 3 or not currency.isalpha() or currency != currency.upper():
            raise CSVExportError(f"row {row_number}: currency must be a three-letter uppercase code")
        return normalized

    def _build_snapshot(self, rows: list[dict[str, Any]]) -> AccountSnapshot:
        account_ids = {str(row["account_id"]) for row in rows}
        account_names = {str(row["account_name"]) for row in rows}
        currencies = {str(row["currency"]) for row in rows}
        if len(account_ids) != 1:
            raise CSVExportError("export must contain exactly one account_id")
        if len(account_names) != 1:
            raise CSVExportError("export must contain exactly one account_name")
        if len(currencies) != 1:
            raise CSVExportError("export must contain exactly one currency")

        campaigns: dict[str, dict[str, Any]] = {}
        creatives: dict[str, dict[str, Any]] = {}
        conversions: dict[str, Decimal] = {}
        budgets: dict[tuple[str, date], Decimal] = {}
        row_grains: set[tuple[date, str, str]] = set()
        total_spend = Decimal("0")
        for row in rows:
            campaign_id = str(row["campaign_id"])
            creative_id = str(row["creative_id"])
            row_grain = (row["date"], campaign_id, creative_id)
            if row_grain in row_grains:
                raise CSVExportError(
                    "export contains duplicate additive row grain "
                    f"({row['date'].isoformat()}, {campaign_id}, {creative_id})"
                )
            row_grains.add(row_grain)
            campaign_identity = (str(row["campaign_name"]), str(row["campaign_status"]))
            existing_campaign = campaigns.get(campaign_id)
            if existing_campaign and (existing_campaign["name"], existing_campaign["status"]) != campaign_identity:
                raise CSVExportError(f"campaign_id {campaign_id!r} has conflicting identity fields")
            if not existing_campaign:
                existing_campaign = {
                    "campaign_id": campaign_id,
                    "name": campaign_identity[0],
                    "status": campaign_identity[1],
                    "spend": Decimal("0"),
                }
                campaigns[campaign_id] = existing_campaign
            existing_campaign["spend"] += row["spend"]
            total_spend += row["spend"]

            creative = {
                "creative_id": creative_id,
                "campaign_id": campaign_id,
                "name": str(row["creative_name"]),
            }
            if creative_id in creatives and creatives[creative_id] != creative:
                raise CSVExportError(f"creative_id {creative_id!r} has conflicting identity fields")
            creatives[creative_id] = creative

            action = str(row["conversion_action"])
            conversions[action] = conversions.get(action, Decimal("0")) + row["conversions"]

            budget_key = (campaign_id, row["date"])
            if budget_key in budgets and budgets[budget_key] != row["budget"]:
                raise CSVExportError(
                    f"campaign_id {campaign_id!r} has conflicting budget values for {row['date'].isoformat()}"
                )
            budgets[budget_key] = row["budget"]

        snapshot: AccountSnapshot = {
            "schema_version": "1.0.0",
            "account": {
                "platform": self.platform,
                "account_id": next(iter(account_ids)),
                "name": next(iter(account_names)),
            },
            "window": {
                "start": min(row["date"] for row in rows).isoformat(),
                "end": max(row["date"] for row in rows).isoformat(),
            },
            "currency": next(iter(currencies)),
            "spend": _number(total_spend),
            "campaigns": [
                {**campaign, "spend": _number(campaign["spend"])}
                for _, campaign in sorted(campaigns.items())
            ],
            "creatives": [creative for _, creative in sorted(creatives.items())],
            "conversions": [
                {"action": action, "count": _number(count)}
                for action, count in sorted(conversions.items())
            ],
            "budgets": [
                {"campaign_id": campaign_id, "date": budget_date.isoformat(), "amount": _number(amount)}
                for (campaign_id, budget_date), amount in sorted(budgets.items())
            ],
        }
        try:
            validate_contract("account-snapshot", snapshot)
        except ContractError as exc:
            raise CSVExportError(f"normalized snapshot violates AccountSnapshot contract: {exc}") from exc
        return snapshot
