from __future__ import annotations

import copy
import json
import os
import stat
import tomllib
from pathlib import Path

import pytest

from claude_ads_core.cli import main
from claude_ads_core.contracts import validate_contract
from claude_ads_core.reporting import (
    PDFDependencyError,
    ReportRenderError,
    atomic_write_report,
    render_html,
    render_markdown,
    render_pdf,
    resolve_report_path,
)


FIXTURE_ROOT = Path(__file__).resolve().parents[1] / "fixtures" / "reports"
BUNDLE_PATH = FIXTURE_ROOT / "sanitized-report-bundle.json"
REPO_ROOT = Path(__file__).resolve().parents[2]


def load_bundle() -> dict:
    return json.loads(BUNDLE_PATH.read_text(encoding="utf-8"))


def test_product_manifest_advertises_only_executable_report_formats():
    manifest = json.loads(
        (REPO_ROOT / "control-plane" / "manifests" / "product-manifest.json").read_text(
            encoding="utf-8"
        )
    )
    assert manifest["human_renderers"] == ["markdown", "html", "pdf"]
    for output_format in manifest["human_renderers"]:
        assert output_format in {"markdown", "html", "pdf"}

    project = tomllib.loads((REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    assert any(
        requirement.startswith("weasyprint>=")
        for requirement in project["project"]["optional-dependencies"]["pdf"]
    )


def test_sanitized_report_fixture_is_a_valid_bundle():
    validate_contract("report-bundle", load_bundle())


def test_markdown_matches_golden_report():
    expected = (FIXTURE_ROOT / "sanitized-report.md").read_text(encoding="utf-8").rstrip("\n") + "\n"
    assert render_markdown(load_bundle()) == expected


def test_html_matches_golden_report_and_is_self_contained():
    expected = (FIXTURE_ROOT / "sanitized-report.html").read_text(encoding="utf-8").rstrip("\n") + "\n"
    rendered = render_html(load_bundle())
    assert rendered == expected
    lowered = rendered.lower()
    assert "<script" not in lowered
    assert "<link" not in lowered
    assert " src=" not in lowered
    assert " url(" not in lowered


def test_rendering_is_reproducible_and_does_not_mutate_input():
    bundle = load_bundle()
    original = copy.deepcopy(bundle)
    assert render_markdown(bundle) == render_markdown(bundle)
    assert render_html(bundle) == render_html(bundle)
    assert bundle == original


def test_report_surfaces_partial_provisional_evidence_contradictions_and_actions():
    markdown = render_markdown(load_bundle())
    assert "Run completeness: **Partial**" in markdown
    assert "Evidence status: **Provisional**" in markdown
    assert "must not be presented as a complete audit" in markdown
    assert "Campaign eligibility is present" in markdown
    assert "Verify and repair the primary conversion action" in markdown
    assert '{"field":"primary_conversion_status","value":"inactive"}' in markdown


def test_insufficient_evidence_is_visible_and_health_is_not_invented():
    bundle = load_bundle()
    bundle["scoring"].update(health_score=None, evidence_coverage=42.0, status="insufficient_evidence")
    markdown = render_markdown(bundle)
    html = render_html(bundle)
    assert "Evidence status: **Insufficient evidence**" in markdown
    assert "Health score: **Not scored**" in markdown
    assert "Evidence is insufficient for a defensible health score" in markdown
    assert "Evidence status: Insufficient evidence" in html
    assert "Health score<strong>Not scored</strong>" in html


def test_untrusted_content_is_escaped_and_obvious_credentials_and_pii_are_redacted():
    bundle = load_bundle()
    finding = bundle["findings"][0]
    finding["observation"] = (
        "Contact analyst@example.test with access_token=secret-value "
        "and <script>alert('untrusted')</script>."
    )
    finding["evidence"].append(
        {"authorization": "Bearer credential-value", "nested": {"email": "person@example.test"}}
    )
    markdown = render_markdown(bundle)
    rendered_html = render_html(bundle)
    combined = markdown + rendered_html
    assert "analyst@example.test" not in combined
    assert "person@example.test" not in combined
    assert "secret-value" not in combined
    assert "credential-value" not in combined
    assert "<script>" not in rendered_html
    assert "&lt;script&gt;" in rendered_html
    assert "[REDACTED]" in combined


def test_renderer_rejects_invalid_bundle_and_malformed_extensions():
    invalid = load_bundle()
    invalid["schema_version"] = "2.0.0"
    with pytest.raises(ReportRenderError, match="invalid report bundle"):
        render_markdown(invalid)

    invalid = load_bundle()
    invalid["actions"] = {"action": "not an array"}
    with pytest.raises(ReportRenderError, match=r"\$\.actions"):
        render_html(invalid)


@pytest.mark.parametrize("destination", ["../outside.md", "/tmp/outside.md", "nested/../../outside.md"])
def test_safe_report_path_rejects_absolute_and_traversal_paths(tmp_path, destination):
    with pytest.raises(ReportRenderError, match="relative path"):
        resolve_report_path(tmp_path / "reports", destination)


def test_safe_report_path_rejects_parent_and_destination_symlinks(tmp_path):
    root = tmp_path / "reports"
    root.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    try:
        (root / "linked").symlink_to(outside, target_is_directory=True)
        (root / "report.md").symlink_to(outside / "report.md")
    except OSError as exc:
        pytest.skip(f"symlinks unavailable: {exc}")
    with pytest.raises(ReportRenderError, match="parent must not be a symlink"):
        resolve_report_path(root, "linked/report.md")
    with pytest.raises(ReportRenderError, match="output must not be a symlink"):
        resolve_report_path(root, "report.md")


def test_atomic_report_write_uses_private_permissions_and_leaves_no_temp_file(tmp_path):
    output = atomic_write_report(tmp_path / "reports", "run-1/report.md", "report\n")
    assert output.read_text(encoding="utf-8") == "report\n"
    if os.name != "nt":
        assert stat.S_IMODE(output.stat().st_mode) == 0o600
    assert list(output.parent.glob(".report.md.*")) == []


def test_pdf_bridge_fails_clearly_when_optional_dependency_is_unavailable(monkeypatch):
    def unavailable(name: str):
        raise ImportError(name)

    monkeypatch.setattr("claude_ads_core.reporting.importlib.import_module", unavailable)
    with pytest.raises(PDFDependencyError, match="optional 'weasyprint'"):
        render_pdf(load_bundle())


def test_real_pdf_render_smoke_when_runtime_dependencies_are_installed():
    pytest.importorskip("weasyprint")
    rendered = render_pdf(load_bundle())
    assert rendered.startswith(b"%PDF-")
    assert len(rendered) > 1_000


def test_cli_render_writes_validated_report_under_safe_root(tmp_path, capsys):
    root = tmp_path / "runs"
    assert main(["render", str(BUNDLE_PATH), "--format", "html", "--root", str(root)]) == 0
    result = json.loads(capsys.readouterr().out)
    output = root / "fixture-run-20260711-001" / "report.html"
    assert result == {
        "format": "html",
        "path": str(output),
        "run_id": "fixture-run-20260711-001",
        "status": "rendered",
    }
    assert output.read_text(encoding="utf-8") == render_html(load_bundle())


def test_cli_render_returns_machine_readable_error_for_unsafe_output(tmp_path, capsys):
    assert (
        main(
            [
                "report",
                str(BUNDLE_PATH),
                "--root",
                str(tmp_path / "runs"),
                "--output",
                "../outside.md",
            ]
        )
        == 2
    )
    result = json.loads(capsys.readouterr().err)
    assert result["status"] == "invalid"
    assert "relative path" in result["error"]
