"""Clean-room repository and complete fork-survey contract tests."""

from __future__ import annotations

import json
import re


FORKS = {
    "andersonamaral2/claude-ads": ("main", "b661972ae2daadac5f8331fa7e6a8bf699c8fc53", "MIT", "ahead", 9, 0, 1, 22, 0),
    "xmilresearch-lab/claude-ads": ("main", "4f70490445d71ebdd13012e907b531874e510747", "NOASSERTION", "diverged", 110, 47, 101, 5, 16007),
    "louisgiuliani/claude-ads": ("main", "d20b304c9320aea84d6cf9683351739d300d23f7", "MIT", "ahead", 2, 0, 1, 25, 0),
    "chizee/claude-ads": ("main", "4a64b6d79f635b5beaf0a63162ec6ee63a780107", "MIT", "ahead", 1, 0, 1, 6, 0),
    "zoeresonance/claude-ads": ("main", "a404ca54034beeb383cde681c523fdeeb76ed0a4", "MIT", "diverged", 101, 30, 39, 14632, 0),
    "seeksi/claude-ads": ("main", "73f9879a0b4abf0396b6cc22dc7251b678a5595d", "MIT", "ahead", 1, 0, 6, 71, 64),
    "imitrushi/claude-ads": ("main", "335ae56abdee5f16506f740573c46dcd21f97954", "MIT", "ahead", 1, 0, 63, 34348, 0),
    "qant-au/claude-ads": ("main", "600162424878674a0642d63540a3faea274f748b", "MIT", "ahead", 3, 0, 2, 17, 0),
    "pankajthakur1907/claude-ads": ("main", "a346b823e7e5e5e894d00936b32cb16b140150e0", "MIT", "ahead", 4, 0, 3, 636, 0),
    "TIQamitsharma/claude-ads": ("main", "19ae231271a8014fcaa0589a174f41ed87fb03e6", "MIT", "diverged", 14, 47, 94, 17411, 0),
    "haruki1987/claude-ads": ("main", "7ab30bac84badb37952834aa7bb33d465d98f4ef", "MIT", "ahead", 4, 0, 10, 1038, 20),
    "juliandickie/pro-marketing-ads": ("pro-marketing-ads", "0a093490571b593cd0d6f84e49c5dad455d0622d", "MIT", "ahead", 11, 0, 23, 340, 122),
    "emolina95/claude-ads": ("main", "ed0a49e4d99d18c624b7fb5d6cabdeaf9ba226d9", "MIT", "diverged", 1, 30, 1, 10, 0),
    "josephcrown920/claude-ads": ("main", "f52ea8f9f732350db58df1ffce93a33b2afeb1b9", "MIT", "diverged", 1, 36, 3, 297, 0),
    "kutzki/antigravity-ads": ("main", "8a01da521f3c036a42d76d1959322c2fec5ade8f", "NOASSERTION", "no-common-ancestor", None, None, None, None, None),
    "ltshabari/claude-ads": ("main", "f467d31bb24873f8b09c9918dfc1a2196489e352", "MIT", "diverged", 1, 30, 2, 32, 1),
    "redpointgroup/claude-ads": ("main", "7e634f21a8f737580f0ad3e9eefdb92259104f32", "MIT", "diverged", 2, 30, 4, 381, 0),
}

EXTERNAL_REPOSITORIES = {
    "zubair-trabzada/ai-ads-claude": ("main", "d1df3f544249191cbc600c8301e2b9d5ddd121c8", "MIT", 29),
    "ivangfalco/ads-skills": ("main", "926bf75e20a833012ca1c7aeb514209411541fd6", "NOASSERTION", 105),
    "mathiaschu/meta-ads-analyzer": ("main", "9088472ddacdb89f3c5943c3db6be7b8ee25c922", "MIT", 16),
    "mathiaschu/google-ads-analyzer": ("master", "9ae39c23bc73ac6fca1c7fbb3d75002e0d97aaca", "MIT", 19),
    "gomarble-ai/facebook-ads-mcp-server": ("main", "1a9406e9a8ccdab9260926075bd4a439140b0f81", "MIT", 10),
    "gomarble-ai/google-ads-mcp-server": ("main", "eb8f1fa3cb3e1957df14755003026d76b87c6498", "MIT", 12),
    "googleads/google-ads-mcp": ("main", "1c9817a616b0221a2790286edf6a443397ee1bb4", "Apache-2.0", 51),
    "googleanalytics/google-analytics-mcp": ("main", "c09abcba1c565f191351169894d61b54a2502e17", "Apache-2.0", 29),
    "irinabuht12-oss/google-meta-ads-ga4-mcp": ("main", "eb87b027ebbc62844c06116a3b1071b83567e3a5", "MIT", 16),
    "TheMattBerman/google-ads-copilot": ("main", "2c253ee988b5540465317cde0cd4d6915dc2b382", "MIT", 132),
    "AdsMCP/tiktok-ads-mcp-server": ("main", "fef46dda014716773f97473a0044bdfae123d99f", "MIT", 22),
    "KuudoAI/amazon_ads_mcp": ("main", "ec8cf462b32566600d069168f4c1c212f954cb00", "MIT", 554),
    "aaron-he-zhu/aaron-marketing-skills": ("main", "661c5701d75ef5a537013f714da3672836cd2dd6", "Apache-2.0", 555),
    "Hainrixz/claude-ads": ("main", "11c2e98792744c0371bcf12c389eec18c129052a", "MIT", 159),
    "zubair-trabzada/ai-marketing-claude": ("main", "e5aa0ea4c5f30d8bc08771e8ea932463e76d3356", "MIT", 37),
    "pipeboard-co/meta-ads-mcp": ("main", "225f46f5586a66add4e30cca218c5e88982e066c", "NOASSERTION", 111),
}

TRACKERS = {
    ("Hainrixz/claude-ads", 1): ("pull-request", "closed", False, "already-addressed"),
    ("Hainrixz/claude-ads", 2): ("pull-request", "closed", False, "already-addressed"),
    ("Hainrixz/claude-ads", 3): ("pull-request", "closed", False, "already-addressed"),
    ("Hainrixz/claude-ads", 4): ("pull-request", "closed", False, "already-addressed"),
    ("Hainrixz/claude-ads", 5): ("pull-request", "closed", False, "already-addressed"),
    ("Hainrixz/claude-ads", 6): ("pull-request", "closed", False, "already-addressed"),
    ("Hainrixz/claude-ads", 7): ("pull-request", "open", False, "defer"),
    ("mathiaschu/meta-ads-analyzer", 1): ("pull-request", "open", False, "reject"),
    ("mathiaschu/meta-ads-analyzer", 2): ("issue", "open", False, "reject"),
    ("mathiaschu/meta-ads-analyzer", 3): ("pull-request", "open", False, "already-addressed"),
    ("mathiaschu/google-ads-analyzer", 1): ("issue", "closed", False, "already-addressed"),
    ("mathiaschu/google-ads-analyzer", 2): ("pull-request", "open", False, "already-addressed"),
    ("TheMattBerman/google-ads-copilot", 1): ("pull-request", "closed", True, "already-addressed"),
    ("TheMattBerman/google-ads-copilot", 2): ("pull-request", "closed", True, "adopt"),
}

SHA_RE = re.compile(r"^[0-9a-f]{40}$")
ID_RE = re.compile(r"^(fork|repo)-[a-z0-9-]+$")
CONCEPT_RE = re.compile(r"^RC-[0-9]{4}$")
TRACKER_RE = re.compile(r"^TRK-[0-9]{4}$")
REQUIREMENT_RE = re.compile(r"^REQ-[A-Z]+-[0-9]{3}$")


def _load(repo_root, kind: str, name: str) -> dict:
    return json.loads(
        (repo_root / "control-plane" / kind / name).read_text(encoding="utf-8")
    )


def test_manifest_matches_declared_schema_surface(repo_root):
    schema = _load(repo_root, "schemas", "repository-review-ledger.schema.json")
    manifest = _load(repo_root, "manifests", "repository-review-ledger.json")

    assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    assert schema["$id"].endswith("repository-review-ledger.v1.json")
    assert set(manifest) == set(schema["required"])
    assert manifest["schema_version"] == "1.0.0"
    assert manifest["reviewed_at"] == "2026-07-11"
    assert manifest["clean_room_policy"] == "concepts-only-no-code-or-prose"

    repository_schema = schema["$defs"]["repository_review"]
    repository_required = set(repository_schema["required"])
    repository_allowed = set(repository_schema["properties"])
    concept_schema = schema["$defs"]["actionable_concept"]
    concept_required = set(concept_schema["required"])
    concept_allowed = set(concept_schema["properties"])
    head_schema = schema["$defs"]["head_review"]
    head_required = set(head_schema["required"])
    head_allowed = set(head_schema["properties"])

    for review in manifest["repositories"]:
        assert set(review) == repository_required == repository_allowed
        assert ID_RE.fullmatch(review["id"])
        assert SHA_RE.fullmatch(review["reviewed_head_sha"])
        assert set(review["head_review"]) >= head_required
        assert set(review["head_review"]) <= head_allowed
        for concept in review["actionable_concepts"]:
            assert set(concept) == concept_required == concept_allowed
            assert CONCEPT_RE.fullmatch(concept["id"])
            assert all(REQUIREMENT_RE.fullmatch(item) for item in concept["requirement_ids"])


def test_paginated_fork_census_is_complete_and_reconciled(repo_root):
    manifest = _load(repo_root, "manifests", "repository-review-ledger.json")
    survey = manifest["fork_survey"]
    forks = [item for item in manifest["repositories"] if item["relationship"] == "fork"]

    assert survey["upstream_repository"] == "AgriciDaniel/claude-ads"
    assert survey["upstream_head_sha"] == "283d9d4917cb7c4f2ce9181e125bb1970f74ab04"
    assert survey["paginated_fork_count"] == 1026
    assert survey["repository_counter_observed"] == 1023
    assert survey["ancestor_or_equal_count"] == 1009
    assert survey["non_ancestor_count"] == 17
    assert survey["ancestor_or_equal_count"] + survey["non_ancestor_count"] == survey["paginated_fork_count"]
    assert survey["completeness"] == "complete"
    assert len(forks) == 17
    assert set(survey["non_ancestor_repository_ids"]) == {item["id"] for item in forks}


def test_all_divergent_default_heads_have_exact_compare_evidence(repo_root):
    manifest = _load(repo_root, "manifests", "repository-review-ledger.json")
    reviews = {
        item["repository"]: item
        for item in manifest["repositories"]
        if item["relationship"] == "fork"
    }
    assert set(reviews) == set(FORKS)

    for repository, expected in FORKS.items():
        branch, head, license_spdx, status, ahead, behind, files, additions, deletions = expected
        review = reviews[repository]
        evidence = review["head_review"]
        assert review["default_branch"] == branch
        assert review["reviewed_head_sha"] == head
        assert review["license_spdx"] == license_spdx
        assert evidence["compare_status"] == status
        assert review["actionable_concepts"]
        if status == "no-common-ancestor":
            assert evidence["method"] == "github-rest-compare-plus-tree"
            assert evidence["tree_blob_count"] == 110
            for field in ("ahead_by", "behind_by", "changed_files", "additions", "deletions"):
                assert field not in evidence
        else:
            assert evidence["method"] == "github-rest-compare"
            assert evidence["ahead_by"] == ahead
            assert evidence["behind_by"] == behind
            assert evidence["changed_files"] == files
            assert evidence["additions"] == additions
            assert evidence["deletions"] == deletions


def test_external_heads_and_licenses_are_pinned(repo_root):
    manifest = _load(repo_root, "manifests", "repository-review-ledger.json")
    reviews = {
        item["repository"]: item
        for item in manifest["repositories"]
        if item["relationship"] == "external"
    }
    assert set(reviews) == set(EXTERNAL_REPOSITORIES)

    for repository, (branch, head, license_spdx, blobs) in EXTERNAL_REPOSITORIES.items():
        review = reviews[repository]
        assert review["default_branch"] == branch
        assert review["reviewed_head_sha"] == head
        assert review["license_spdx"] == license_spdx
        assert review["head_review"]["method"] == "github-rest-tree-and-metadata"
        assert review["head_review"]["tree_blob_count"] == blobs


def test_license_and_clean_room_rules_block_unlicensed_transfer(repo_root):
    manifest = _load(repo_root, "manifests", "repository-review-ledger.json")
    noassertion = set()
    concept_ids = []
    dispositions = set(manifest["disposition_semantics"])

    assert dispositions == {"adopt", "already-addressed", "defer", "reject"}
    for review in manifest["repositories"]:
        assert review["copy_policy"] == "concepts-only-no-code-or-prose"
        assert review["source_url"] == f"https://github.com/{review['repository']}"
        assert review["primary_disposition"] in dispositions
        if review["license_spdx"] == "NOASSERTION":
            noassertion.add(review["repository"])
            assert review["license_use"] == "unverified-metadata-only"
            assert review["primary_disposition"] != "adopt"
        for concept in review["actionable_concepts"]:
            assert concept["disposition"] in dispositions
            concept_ids.append(concept["id"])

    assert noassertion == {
        "xmilresearch-lab/claude-ads",
        "kutzki/antigravity-ads",
        "ivangfalco/ads-skills",
        "pipeboard-co/meta-ads-mcp",
    }
    assert len(concept_ids) == 41
    assert len(concept_ids) == len(set(concept_ids))
    assert {concept["disposition"] for item in manifest["repositories"] for concept in item["actionable_concepts"]} == dispositions


def test_selected_trackers_are_exhaustive_as_of_review_date(repo_root):
    manifest = _load(repo_root, "manifests", "repository-review-ledger.json")
    items = {(item["repository"], item["number"]): item for item in manifest["tracker_items"]}
    scopes = {scope["repository"]: scope for scope in manifest["tracker_scopes"]}
    all_concepts = {
        concept["id"]
        for review in manifest["repositories"]
        for concept in review["actionable_concepts"]
    }

    assert len(items) == len(manifest["tracker_items"]) == 14
    assert set(items) == set(TRACKERS)
    assert set(scopes) == {
        "Hainrixz/claude-ads",
        "mathiaschu/meta-ads-analyzer",
        "mathiaschu/google-ads-analyzer",
        "TheMattBerman/google-ads-copilot",
    }

    for key, expected in TRACKERS.items():
        item = items[key]
        kind, state, merged, disposition = expected
        assert TRACKER_RE.fullmatch(item["id"])
        assert (item["kind"], item["state"], item["merged"], item["disposition"]) == expected
        suffix = "pull" if kind == "pull-request" else "issues"
        assert item["url"] == f"https://github.com/{item['repository']}/{suffix}/{item['number']}"
        assert set(item["linked_concept_ids"]) <= all_concepts

    for repository, scope in scopes.items():
        scoped = [item for item in manifest["tracker_items"] if item["repository"] == repository]
        assert scope["state_filter"] == "all"
        assert scope["completeness"] == "complete"
        assert scope["issue_count"] == sum(item["kind"] == "issue" for item in scoped)
        assert scope["pull_request_count"] == sum(item["kind"] == "pull-request" for item in scoped)
        assert set(scope["item_ids"]) == {item["id"] for item in scoped}


def test_ledger_retains_no_raw_review_payloads_or_local_paths(repo_root):
    manifest = _load(repo_root, "manifests", "repository-review-ledger.json")
    forbidden_keys = {
        "body",
        "code",
        "diff",
        "excerpt",
        "patch",
        "raw_content",
        "transcript",
    }

    def walk(value):
        if isinstance(value, dict):
            assert not (set(value) & forbidden_keys)
            for nested in value.values():
                walk(nested)
        elif isinstance(value, list):
            for nested in value:
                walk(nested)

    walk(manifest)
    serialized = json.dumps(manifest, sort_keys=True)
    assert "/var/home/" not in serialized
    assert "/Users/" not in serialized
    assert "C:\\" not in serialized
    assert "access_token" not in serialized.lower()
