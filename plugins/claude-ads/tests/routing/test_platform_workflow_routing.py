"""Metadata-level collision tests for platform and lifecycle routing.

These are deterministic guards around skill descriptions. Model-level forward
evaluations remain a separate release gate.
"""

from __future__ import annotations

import json
import re
from pathlib import Path


STOP = {
    "a", "an", "and", "or", "the", "to", "for", "from", "with", "our",
    "my", "of", "in", "on", "paid", "ads", "ad", "campaign", "campaigns",
    "audit", "review", "use", "when",
}


def _tokens(text: str) -> set[str]:
    return {
        token
        for token in re.findall(r"[a-z0-9+]+", text.lower())
        if len(token) > 1 and token not in STOP
    }


def _score(prompt: str, description: str) -> int:
    return len(_tokens(prompt) & _tokens(description))


def test_platform_and_workflow_descriptions_win_declared_collisions(skill_descriptions, repo_root: Path):
    fixture = json.loads(
        (repo_root / "evals" / "platform-workflow-routing.json").read_text(encoding="utf-8")
    )
    failures: list[str] = []
    for case in fixture:
        expected = case["expected_skill"]
        expected_desc = skill_descriptions.get(expected)
        if expected_desc is None:
            failures.append(f"{case['id']}: missing expected skill {expected}")
            continue
        expected_score = _score(case["prompt"], expected_desc)
        if expected_score < 2:
            failures.append(f"{case['id']}: expected description has weak score {expected_score}")
        for forbidden in case["forbidden_skills"]:
            forbidden_desc = skill_descriptions.get(forbidden)
            if forbidden_desc is None:
                failures.append(f"{case['id']}: missing forbidden skill {forbidden}")
                continue
            forbidden_score = _score(case["prompt"], forbidden_desc)
            if expected_score <= forbidden_score:
                failures.append(
                    f"{case['id']}: {expected} score {expected_score} does not beat "
                    f"{forbidden} score {forbidden_score}"
                )
    assert not failures, "Routing description collisions:\n  " + "\n  ".join(failures)


def test_near_miss_language_does_not_appear_as_paid_platform_intent(skill_descriptions):
    near_misses = {
        "ads-reddit": "Write moderation rules for an organic subreddit community",
        "ads-pinterest": "Pin this note to the project dashboard",
        "ads-snapchat": "Take a quick snapshot of the local test results",
        "ads-x": "Label the x axis on this performance chart",
    }
    for skill, prompt in near_misses.items():
        description = skill_descriptions[skill]
        assert _score(prompt, description) < 2, f"near miss overlaps too broadly with {skill}"
