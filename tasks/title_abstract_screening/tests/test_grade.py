# Behavior -> test
#   oracle scores 1.0                        -> test_oracle_scores_perfect_reward_and_recall
#   false positives lower reward             -> test_false_positive_lowers_reward_but_preserves_recall
#   missing decisions fail format validation -> test_missing_decisions_are_format_failure_not_silent_excludes
#   false negatives lower reward             -> test_dropping_true_include_lowers_reward
#   degenerate baselines stay bounded        -> test_degenerate_baselines_bounded
#   details expose errors and full matrix     -> test_reward_details_include_full_matrix_and_error_buckets
#   reward JSON stays numeric                 -> test_write_keeps_reward_json_numeric_and_writes_details
#   only include/exclude labels parse         -> test_rejects_labels_outside_include_exclude

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest
from pydantic import ValidationError

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("screening_grade", HERE / "grade.py")
G = importlib.util.module_from_spec(spec)
sys.modules["screening_grade"] = G
assert spec.loader is not None
spec.loader.exec_module(G)

ScreenHuman = G.ScreenHuman
ScreenOut = G.ScreenOut
build_details = G.build_details
grade_screening = G.grade_screening


def _human(include: dict[str, bool]) -> ScreenHuman:
    return ScreenHuman(review_id="T", include=include)


def test_oracle_scores_perfect_reward_and_recall() -> None:
    human = _human({"a": True, "b": False, "c": False, "d": True})
    pred = ScreenOut(
        decisions={
            "a": "include",
            "b": "exclude",
            "c": "exclude",
            "d": "include",
        }
    )

    scores = grade_screening(pred, human)

    assert scores["reward"] == 1.0
    assert scores["recall"] == 1.0


def test_false_positive_lowers_reward_but_preserves_recall() -> None:
    human = _human({"a": True, "b": False, "c": False, "d": True})
    pred = ScreenOut(
        decisions={
            "a": "include",
            "b": "include",
            "c": "exclude",
            "d": "include",
        }
    )

    scores = grade_screening(pred, human)

    # Recall stays perfect; the false inclusion incurs asymmetric disagreement cost.
    assert scores["recall"] == 1.0
    assert scores["precision"] == pytest.approx(2 / 3)
    assert scores["specificity"] == 0.5
    assert scores["f1"] == pytest.approx(0.8)
    assert scores["reward"] == pytest.approx(1 - 1 / 6.5)
    assert scores["reward"] < 1.0


def test_missing_decisions_are_format_failure_not_silent_excludes() -> None:
    human = _human({"a": True, "b": True, "c": False, "d": False})
    pred = ScreenOut(decisions={"a": "include", "b": "include"})

    scores = grade_screening(pred, human)

    assert scores["key_set_match"] == 0.0
    assert scores["missing_decisions"] == 2
    assert scores["reward"] == 0.0


def test_dropping_true_include_lowers_reward() -> None:
    human = _human({"a": True, "b": True, "c": False})
    pred = ScreenOut(
        decisions={
            "a": "include",
            "b": "exclude",
            "c": "exclude",
        }
    )

    scores = grade_screening(pred, human, target_recall=0.95)

    # Missing an include halves recall and is penalized at 10x a false positive.
    assert scores["recall"] == 0.5
    assert scores["meets_recall_target"] == 0.0
    assert scores["f1"] == pytest.approx(2 / 3)
    assert scores["reward"] == pytest.approx(1 - 10 / (41 / 3))
    assert scores["reward"] < 1.0


def test_degenerate_baselines_bounded() -> None:
    """Anti-gaming floors: screen-out-all -> 0, oracle -> 1, include-all stays below the
    truth. Both constant classifiers are exactly chance-level."""
    human = _human({**{f"inc{i}": True for i in range(2)}, **{f"exc{i}": False for i in range(8)}})
    ids = list(human.include)
    include_all = ScreenOut(decisions={i: "include" for i in ids})
    out_all = ScreenOut(decisions={i: "exclude" for i in ids})
    oracle = ScreenOut(decisions={i: ("include" if human.include[i] else "exclude") for i in ids})

    assert grade_screening(out_all, human)["reward"] == 0.0
    assert grade_screening(oracle, human)["reward"] == 1.0
    include = grade_screening(include_all, human)["reward"]
    assert include == 0.0


def test_false_negative_costs_more_than_false_positive() -> None:
    human = ScreenHuman(
        review_id="x",
        include={"p1": True, "p2": True, "n1": False, "n2": False},
    )
    one_false_positive = ScreenOut(
        decisions={"p1": "include", "p2": "include", "n1": "include", "n2": "exclude"}
    )
    one_false_negative = ScreenOut(
        decisions={"p1": "include", "p2": "exclude", "n1": "exclude", "n2": "exclude"}
    )

    fp_scores = grade_screening(one_false_positive, human)
    fn_scores = grade_screening(one_false_negative, human)

    assert fp_scores["reward"] == pytest.approx(1 - 1 / 6.5)
    assert fn_scores["reward"] == pytest.approx(1 - 10 / 15.5)
    assert fn_scores["reward"] < fp_scores["reward"]


def test_reward_details_include_full_matrix_and_error_buckets() -> None:
    human = _human({"a": True, "b": False, "c": False, "d": True})
    pred = ScreenOut(
        decisions={
            "a": "exclude",
            "b": "include",
            "c": "exclude",
            "d": "include",
            "extra": "include",
        }
    )

    scores = grade_screening(pred, human)
    details = build_details(pred, human, scores)

    assert details["task"] == "title_abstract_screening"
    assert details["review_id"] == "T"
    assert len(details["items"]) == 4
    by_id = {item["study_id"]: item for item in details["items"]}
    assert by_id["a"] == {
        "study_id": "a",
        "expected": "include",
        "observed": "exclude",
        "correct": False,
        "error_type": "false_negative",
    }
    assert by_id["b"]["error_type"] == "false_positive"
    assert by_id["c"]["correct"] is True
    assert by_id["d"]["correct"] is True
    assert [item["study_id"] for item in details["errors"]["false_negatives"]] == ["a"]
    assert [item["study_id"] for item in details["errors"]["false_positives"]] == ["b"]
    assert details["errors"]["extra_decisions"] == [
        {
            "study_id": "extra",
            "expected": None,
            "observed": "include",
            "correct": False,
            "error_type": "extra_decision",
        }
    ]


def test_write_keeps_reward_json_numeric_and_writes_details(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    human = _human({"a": True, "b": False})
    pred = ScreenOut(decisions={"a": "include", "b": "exclude"})
    scores = grade_screening(pred, human)
    details = build_details(pred, human, scores)
    monkeypatch.setattr(G, "OUT", tmp_path)

    G._write(scores, float(scores["reward"]), details)

    reward = json.loads((tmp_path / "reward.json").read_text())
    reward_details = json.loads((tmp_path / "reward-details.json").read_text())
    assert reward["reward"] == 1.0
    assert "items" not in reward
    assert reward_details["items"] == details["items"]


@pytest.mark.parametrize("label", ["Include", "maybe", ""])
def test_rejects_labels_outside_include_exclude(label: str) -> None:
    with pytest.raises(ValidationError):
        ScreenOut(decisions={"a": label})
