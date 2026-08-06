"""Contract tests for the primary-source Google updates ledger."""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from urllib.parse import urlparse


REPO_ROOT = Path(__file__).resolve().parents[1]
LEDGER_PATH = REPO_ROOT / "data" / "google-updates.json"
GOOGLE_SKILL_PATH = REPO_ROOT / "skills" / "blog-google" / "SKILL.md"
GOOGLE_CURRENTNESS_PATH = (
    REPO_ROOT / "skills" / "blog-google" / "references" / "search-currentness.md"
)
SCHEMA_SKILL_PATH = REPO_ROOT / "skills" / "blog-schema" / "SKILL.md"
SCHEMA_REFERENCE_PATH = REPO_ROOT / "skills" / "blog" / "references" / "schema-stack.md"
CRAWLER_REFERENCE_PATH = (
    REPO_ROOT / "skills" / "blog" / "references" / "ai-crawler-guide.md"
)


def _load_ledger() -> dict:
    return json.loads(LEDGER_PATH.read_text(encoding="utf-8"))


def _normalized(text: str) -> str:
    return " ".join(text.split())


def test_google_updates_ledger_shape_and_currentness() -> None:
    ledger = _load_ledger()

    assert ledger["schema_version"] == 1
    assert date.fromisoformat(ledger["last_verified"]) >= date(2026, 7, 23)
    assert isinstance(ledger["verified"], list) and ledger["verified"]
    assert isinstance(ledger["unverified"], list)
    assert "must never change scoring" in ledger["policy"]


def test_verified_entries_use_unique_ids_and_google_owned_sources() -> None:
    ledger = _load_ledger()
    entries = ledger["verified"]
    ids = [entry["id"] for entry in entries]

    assert len(ids) == len(set(ids))
    for entry in entries:
        assert set(entry) == {
            "id",
            "event_date",
            "title",
            "source_url",
            "category",
            "applicability",
            "affected_components",
            "summary",
        }
        date.fromisoformat(entry["event_date"])
        assert entry["affected_components"]
        host = urlparse(entry["source_url"]).hostname
        assert host in {
            "blog.google",
            "developers.google.com",
            "status.search.google.com",
        }


def test_ledger_covers_current_search_contracts() -> None:
    ledger_text = LEDGER_PATH.read_text(encoding="utf-8")

    for contract in (
        "FAQ rich results are no longer shown",
        "up to two weeks",
        "Instagram, TikTok, X, and YouTube",
        "no dedicated API",
        "not ranking factors",
        "first 2MB",
        "Back-button hijacking",
    ):
        assert contract in ledger_text


def test_unverified_entries_cannot_masquerade_as_verified() -> None:
    ledger = _load_ledger()
    verified_ids = {entry["id"] for entry in ledger["verified"]}
    unverified_ids = {entry["id"] for entry in ledger["unverified"]}

    assert verified_ids.isdisjoint(unverified_ids)


def test_schema_guidance_matches_current_google_contract() -> None:
    guidance = _normalized(
        "\n".join(
            (
                SCHEMA_SKILL_PATH.read_text(encoding="utf-8"),
                SCHEMA_REFERENCE_PATH.read_text(encoding="utf-8"),
            )
        )
    )

    assert "earns no SEO or AI-readiness credit" in guidance
    assert "one question with user-submitted answers" in guidance
    assert "Course Info" in guidance and "Course list" in guidance
    assert "PracticeProblem" in guidance
    assert "Dataset Search" in guidance
    assert "present in the rendered DOM" in guidance
    assert "40-60 words" not in guidance
    assert "AI citation support" not in guidance


def test_google_currentness_guidance_preserves_api_boundaries() -> None:
    guidance = _normalized(
        "\n".join(
            (
                GOOGLE_SKILL_PATH.read_text(encoding="utf-8"),
                GOOGLE_CURRENTNESS_PATH.read_text(encoding="utf-8"),
            )
        )
    )

    assert "Wait at least one full week" in guidance
    assert "Web Search, Images, Video mode, and News tab separately" in guidance
    assert "PENDING_REEVALUATION" in guidance
    assert "up to two weeks" in guidance
    assert "Do not promise clicks or queries" in guidance
    assert "Instagram, TikTok, X, and YouTube" in guidance
    assert "not a ranking signal" in guidance


def test_crawler_guidance_requires_behavioral_evidence_and_byte_visibility() -> None:
    guidance = _normalized(CRAWLER_REFERENCE_PATH.read_text(encoding="utf-8"))

    assert "first 2MB" in guidance
    assert "not a ranking factor" in guidance
    assert "Legitimate History API use is not a violation by itself" in guidance
    assert "Do not remove the hash" in guidance
    assert "do not force" in guidance
    assert "not injected via JavaScript" not in guidance
