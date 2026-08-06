"""Command-line interface for deterministic Claude Ads core operations."""

from __future__ import annotations

import argparse
from datetime import date
import json
import sys
from pathlib import Path
from typing import Any, Sequence

from . import __version__
from .adapters import AdapterError, GenericCSVExportAdapter
from .contracts import CONTRACT_NAMES, ContractError, load_contract, validate_contract
from .reporting import ReportRenderError, write_report_bundle
from .product_status import ProductStatusError, evaluate_product_status
from .scoring import ScoringError, score_account, score_portfolio


def _read_json(path: str) -> Any:
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ContractError(f"cannot load {path}: {exc}") from exc


def _emit(payload: Any) -> None:
    print(json.dumps(payload, indent=2, sort_keys=True))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="claude-ads-core")
    parser.add_argument("--version", action="version", version=__version__)
    commands = parser.add_subparsers(dest="command", required=True)

    validate = commands.add_parser("validate", help="validate a versioned JSON contract")
    validate.add_argument("contract", choices=CONTRACT_NAMES)
    validate.add_argument("path")

    score = commands.add_parser("score", help="score one account")
    score.add_argument("--controls", required=True)
    score.add_argument("--findings", required=True)
    score.add_argument("--weights", required=True)

    portfolio = commands.add_parser("portfolio", help="aggregate account scores")
    portfolio.add_argument("path", help="JSON array of account score records")

    status = commands.add_parser("status", help="show repository status, or a report bundle when path is supplied")
    status.add_argument("path", nargs="?")
    status.add_argument("--root", default=".")
    status.add_argument("--as-of")
    status.add_argument("--release-gate")

    next_command = commands.add_parser("next", help="show exactly one repository-artifact blocker")
    next_command.add_argument("--root", default=".")
    next_command.add_argument("--as-of", required=True)
    next_command.add_argument("--release-gate")

    render = commands.add_parser(
        "render",
        aliases=["report"],
        help="render a validated report bundle beneath a safe output root",
    )
    render.add_argument("path", help="ReportBundle JSON input")
    render.add_argument("--format", choices=("markdown", "html", "pdf"), default="markdown")
    render.add_argument("--root", default=".claude-ads/runs", help="safe root for report artifacts")
    render.add_argument("--output", help="relative output path; defaults to <run-id>/report.<extension>")

    ingest = commands.add_parser("ingest-export", help="normalize a generic CSV export")
    ingest.add_argument("--platform", required=True)
    ingest.add_argument("path")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        if args.command == "validate":
            load_contract(args.contract, args.path)
            _emit({"contract": args.contract, "path": args.path, "status": "valid"})
        elif args.command == "score":
            controls = _read_json(args.controls)
            findings = _read_json(args.findings)
            weights = _read_json(args.weights)
            if not isinstance(controls, list) or not isinstance(findings, list) or not isinstance(weights, dict):
                raise ScoringError("controls/findings must be arrays and weights must be an object")
            _emit(score_account(controls, findings, weights).to_dict())
        elif args.command == "portfolio":
            accounts = _read_json(args.path)
            if not isinstance(accounts, list):
                raise ScoringError("portfolio input must be an array")
            _emit(score_portfolio(accounts).to_dict())
        elif args.command == "status":
            if args.path:
                bundle = _read_json(args.path)
                validate_contract("report-bundle", bundle)
                scoring = bundle["scoring"]
                manifest = bundle["run_manifest"]
                _emit(
                    {
                        "run_id": manifest["run_id"],
                        "completeness": manifest["completeness"],
                        "health_score": scoring["health_score"],
                        "evidence_coverage": scoring["evidence_coverage"],
                        "status": scoring["status"],
                    }
                )
            else:
                if not args.as_of:
                    raise ProductStatusError("repository status requires --as-of YYYY-MM-DD")
                try:
                    as_of = date.fromisoformat(args.as_of)
                except ValueError as exc:
                    raise ProductStatusError("--as-of must be an ISO 8601 date") from exc
                _emit(
                    evaluate_product_status(
                        args.root, as_of=as_of, release_gate_path=args.release_gate
                    )
                )
        elif args.command == "next":
            try:
                as_of = date.fromisoformat(args.as_of)
            except ValueError as exc:
                raise ProductStatusError("--as-of must be an ISO 8601 date") from exc
            status_payload = evaluate_product_status(
                args.root, as_of=as_of, release_gate_path=args.release_gate
            )
            _emit(
                {
                    "schema_version": status_payload["schema_version"],
                    "as_of": status_payload["as_of"],
                    "selection_policy": status_payload["selection_policy"],
                    "next_blocker": status_payload["next_blocker"],
                }
            )
        elif args.command in {"render", "report"}:
            bundle = load_contract("report-bundle", args.path)
            extension = {"markdown": "md", "html": "html", "pdf": "pdf"}[args.format]
            destination = args.output or f"{bundle['run_manifest']['run_id']}/report.{extension}"
            output_path = write_report_bundle(bundle, args.format, args.root, destination)
            _emit(
                {
                    "format": args.format,
                    "path": str(output_path),
                    "run_id": bundle["run_manifest"]["run_id"],
                    "status": "rendered",
                }
            )
        elif args.command == "ingest-export":
            _emit(GenericCSVExportAdapter(args.platform).read_snapshot(args.path))
    except (AdapterError, ContractError, ProductStatusError, ReportRenderError, ScoringError) as exc:
        print(json.dumps({"status": "invalid", "error": str(exc)}, sort_keys=True), file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
