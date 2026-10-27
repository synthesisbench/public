"""Nothing gold-bearing may be tracked in this repository, at any depth.

The rules in .gitignore are the first line of defence, but they are written as
path globs and a glob silently stops matching when the layout changes. That is
not hypothetical: `datasets/metapsy/source/*/ref-standard.json` guarded gold
correctly while every review sat directly under `source/`, and stopped guarding
anything the moment a task nested its reviews one level deeper. The files were
still ignored by name in the old tree and wide open in the new one.

So these tests do not read .gitignore. They ask Git what is actually tracked and
fail on anything whose *name* or *content* carries answers, wherever it sits.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]

# Filenames that hold materialized gold. Gold lives in the private monorepo.
GOLD_FILENAMES = frozenset({"ref-standard.json"})

# Directory segments that carry answers when they sit under datasets/. The same
# names under tasks/ are the task contract's demonstration solution over a
# synthetic fixture, which is how `harbor run -a oracle` replays a task at all.
GOLD_DIR_ROOT = "datasets"
GOLD_DIR_SEGMENTS = (
    ("tests", "human"),
    ("solution",),
)

# Top-level JSON keys that are answer maps regardless of the file they live in.
#
GOLD_KEYS = frozenset(
    {"screen_human", "rob_human", "extract_human", "positive_candidate_ids"}
)

# The only thing allowed under datasets/: the agent-facing RoB guidance. Curation, instances, oracle replays, verifier evidence, source
# staging, upstream packages, and run reports all moved to the private monorepo.
DATASET_ALLOWLIST = ("datasets/metapsy/resources/",)


def tracked_files() -> list[Path]:
    out = subprocess.run(
        ["git", "-C", str(ROOT), "ls-files", "-z"],
        stdout=subprocess.PIPE,
        check=True,
    ).stdout
    return [Path(p) for p in out.decode().split("\0") if p]


@pytest.fixture(scope="module")
def tracked() -> list[Path]:
    files = tracked_files()
    assert files, "git ls-files returned nothing; run from inside the repository"
    return files


def test_no_gold_filenames_tracked(tracked: list[Path]) -> None:
    offenders = [str(p) for p in tracked if p.name in GOLD_FILENAMES]
    assert not offenders, (
        "Gold files are tracked:\n  "
        + "\n  ".join(offenders)
    )


def test_no_gold_directories_tracked(tracked: list[Path]) -> None:
    offenders = []
    for path in tracked:
        parts = path.parts
        if not parts or parts[0] != GOLD_DIR_ROOT:
            continue
        for segments in GOLD_DIR_SEGMENTS:
            width = len(segments)
            if any(
                parts[i : i + width] == segments for i in range(len(parts) - width + 1)
            ):
                offenders.append(str(path))
                break
    assert not offenders, (
        "Answer directories are tracked:\n  " + "\n  ".join(sorted(offenders))
    )


def test_no_tracked_json_carries_an_answer_map(tracked: list[Path]) -> None:
    """A renamed gold file is still gold. Look inside every tracked JSON."""
    offenders = []
    for path in tracked:
        if path.suffix != ".json":
            continue
        try:
            payload = json.loads((ROOT / path).read_text())
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            continue
        if isinstance(payload, dict) and GOLD_KEYS & payload.keys():
            offenders.append(f"{path} -> {sorted(GOLD_KEYS & payload.keys())}")
    assert not offenders, (
        "Tracked JSON contains answer maps:\n  " + "\n  ".join(sorted(offenders))
    )


def test_datasets_hold_only_licenses_and_resources(tracked: list[Path]) -> None:
    """Curation and instances rebuild the answer keys, so they may not ship at all.

    Checks both the working tree and the tracked set (ignoring tracked paths
    already deleted on disk, which a pending commit removes).
    """
    on_disk = [
        p.relative_to(ROOT)
        for p in (ROOT / GOLD_DIR_ROOT).rglob("*")
        if p.is_file() and p.name != ".DS_Store"
    ]
    present = [p for p in tracked if p.parts[:1] == (GOLD_DIR_ROOT,) and (ROOT / p).exists()]
    offenders = sorted(
        {str(p) for p in [*on_disk, *present] if not str(p).startswith(DATASET_ALLOWLIST)}
    )
    assert not offenders, "Unexpected dataset files:\n  " + "\n  ".join(offenders[:50])
