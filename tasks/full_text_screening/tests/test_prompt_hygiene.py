from __future__ import annotations

import tomllib
from pathlib import Path


# This file lives at tasks/<task>/tests/, so the tasks/ root is two levels up.
# Reaching any higher walks out of the repository. An earlier version resolved a
# monorepo path that does not exist in a standalone clone: every path below was
# filtered out, and every test in this file passed while checking nothing.
TASKS = Path(__file__).resolve().parents[2]
REPO = TASKS.parent
CANONICAL_PROMPTS = (
    TASKS / "title_abstract_screening/steps/screen/instruction.md",
    TASKS / "full_text_screening/steps/screen/instruction.md",
    TASKS / "full_text_extraction/steps/extract/instruction.md",
    TASKS / "risk_of_bias/steps/judge/instruction.md",
    TASKS / "meta_analysis/steps/meta/instruction.md",
)
PROMPTS = tuple(path for path in CANONICAL_PROMPTS if path.is_file())

# Everything else the agent can read in the public task contract.
AGENT_VISIBLE = tuple(
    path
    for path in (
        *CANONICAL_PROMPTS,
        TASKS / "smoke/instruction.md",
    )
    if path.is_file()
)
TASK_TOMLS = tuple(
    path
    for path in (
        TASKS / "title_abstract_screening/task.toml",
        TASKS / "full_text_screening/task.toml",
        TASKS / "full_text_extraction/task.toml",
        TASKS / "risk_of_bias/task.toml",
        TASKS / "meta_analysis/task.toml",
        TASKS / "smoke/task.toml",
    )
    if path.is_file()
)
# Literal reward vocabulary, plus the phrasings that imply a graded reference without
# ever saying "reward": naming an answer key, a reference value, or the act of matching.
# Those are what a scrub for reward words misses.
FORBIDDEN = (
    "reward",
    "answer key",
    "reference interval",
    "reference tooling",
    "reference meta-analysis",
    "reference answer",
    "expected answer",
    "correct answer",
    "will miss",
    "can be matched",
    "match that convention",
    "count against",
    "counts against",
    "penalis",
    "penaliz",
    "penalty",
    "grader",
    "graded",
    "credit",
    "score",
    "scoring",
    "human row",
    "free extra",
    "tolerance",
    "contradicted",
    "primary score",
    "scores 0",
    "worst error",
    "reproducing the full-text screening stage of a cochrane systematic review",
    "reproducing the full-text extraction stage of a cochrane systematic review",
    "reproducing the risk-of-bias judgement stage of a cochrane systematic review",
    "reproducing the meta-analysis stage of a cochrane systematic review",
    "there is no review text",
    "no list of pre-defined analyses",
)


# Clinical outcome names that legitimately contain a forbidden substring; these
# are agent-visible domain vocabulary, not grading mechanics.
# Clinical instruments name themselves with the word "score". Strip those phrases before
# hunting for grading vocabulary. These are removed in order, so a phrase that survives an
# earlier removal must appear here too: stripping "dizziness impact scale" leaves
# "(dis) score" behind.
ALLOWED_CLINICAL = (
    "pain score",
    "higher scores indicate",
    "baseline scores",
    "dizziness impact scale",
    "(dis) score",
    "dis score",
)


EXPECTED_PROMPTS = 5          # the five graded tasks; smoke has no step instruction
EXPECTED_TASK_TOMLS = 6       # the five graded tasks plus smoke


def test_suite_is_not_vacuous() -> None:
    """The other tests iterate over discovered files. Discover nothing and they all pass
    while checking nothing -- which is what happened when TASKS resolved outside the
    repository: every prompt-hygiene guarantee here was silently unenforced in the
    published repo. Assert the discovery, not only what it finds."""
    assert len(PROMPTS) == EXPECTED_PROMPTS, f"discovered {len(PROMPTS)} prompts, expected {EXPECTED_PROMPTS}"
    assert len(TASK_TOMLS) == EXPECTED_TASK_TOMLS, (
        f"discovered {len(TASK_TOMLS)} task.toml files, expected {EXPECTED_TASK_TOMLS}"
    )


def test_agent_prompts_do_not_expose_grading_mechanics() -> None:
    failures: list[str] = []
    for path in AGENT_VISIBLE:
        text = path.read_text(encoding="utf-8").lower()
        for allowed in ALLOWED_CLINICAL:
            text = text.replace(allowed, "")
        for term in FORBIDDEN:
            if term in text:
                failures.append(f"{path.relative_to(REPO)} contains {term!r}")

    assert failures == []


def test_agent_prompts_are_local_file_only() -> None:
    for path in PROMPTS:
        text = " ".join(path.read_text(encoding="utf-8").lower().split())
        assert "use only the files staged under `/task`" in text
        assert "do not use the web" in text


def test_active_tasks_allow_model_transport_and_keep_verifier_separate() -> None:
    for path in TASK_TOMLS:
        data = tomllib.loads(path.read_text(encoding="utf-8"))
        assert data["environment"]["network_mode"] == "public"
        if path.parent.name == "smoke":
            assert data["agent"].get("network_mode", data["environment"]["network_mode"]) == "public"
            assert "environment_mode" not in data["verifier"]
            continue
        assert data["agent"]["network_mode"] == "public"
        assert data["verifier"]["network_mode"] == "public"
        assert data["verifier"]["environment_mode"] == "separate"
        assert data["verifier"]["environment"]["network_mode"] == "public"
