# Behavior -> test manifest:
# Oracle agreement -> test_oracle_with_overall_bias_predictions_still_scores_one
# All-unclear floor -> test_all_unclear_predictions_score_zero_as_a_degenerate_strategy
# All-low floor -> test_all_low_predictions_score_zero_like_missing_defaults
# Empty-file floor -> test_empty_prediction_scores_zero_despite_majority_low_gold
# High-label path -> test_perfect_prediction_scores_one

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("risk_of_bias_grade", HERE / "grade.py")
G = importlib.util.module_from_spec(spec)
sys.modules["risk_of_bias_grade"] = G
assert spec.loader is not None
spec.loader.exec_module(G)

RobHumanRecord = G.RobHumanRecord
RobOut = G.RobOut
build_details = G.build_details
grade_rob = G.grade_rob


def _record(
    study_id: str,
    judgements: dict[str, str],
    outcome: str | None = None,
) -> RobHumanRecord:
    return RobHumanRecord(
        study_id=study_id,
        outcome=outcome,
        framework="rob2" if outcome else "rob1",
        judgements=judgements,
    )


def _pred(
    study_id: str,
    judgements: dict[str, str],
    outcome: str | None = None,
) -> tuple[str, str, dict[str, str]]:
    return study_id, outcome or G.STUDY_LEVEL, judgements


def _out(*items: tuple[str, str, dict[str, str]]) -> RobOut:
    nested: dict[str, dict[str, dict[str, str]]] = {}
    for study_id, outcome, judgements in items:
        nested.setdefault(study_id, {})[outcome] = judgements
    return RobOut(judgements=nested)


def _mixed_majority_low_human() -> list[RobHumanRecord]:
    return [
        _record(
            "a",
            {
                "D1": "low",
                "D2": "low",
                "D3": "low",
                "D4": "unclear",
                "D5": "high",
            },
        )
    ]


def test_perfect_prediction_scores_one() -> None:
    human = [
        _record("a", {"Random sequence generation": "low", "Blinding": "high"}),
        _record("b", {"Allocation concealment": "unclear"}),
    ]
    pred = _out(
            _pred("a", {"Random sequence generation": "low", "Blinding": "high"}),
            _pred("b", {"Allocation concealment": "unclear"}),
        )

    scores = grade_rob(pred, human)

    assert scores["reward"] == 1.0
    assert scores["kappa"] == 1.0
    assert scores["domain_accuracy"] == 1.0


def test_empty_prediction_scores_zero_despite_majority_low_gold() -> None:
    scores = grade_rob(_out(), _mixed_majority_low_human())

    assert scores["domain_accuracy"] == 3 / 5
    assert scores["kappa"] == 0.0
    assert scores["reward"] == 0.0


def test_all_low_predictions_score_zero_like_missing_defaults() -> None:
    human = _mixed_majority_low_human()
    pred = _out(
            _pred("a", {domain: "low" for domain in human[0].judgements}),
        )

    scores = grade_rob(pred, human)

    assert scores["domain_accuracy"] == 3 / 5
    assert scores["kappa"] == 0.0
    assert scores["reward"] == 0.0


def test_all_unclear_predictions_score_zero_as_a_degenerate_strategy() -> None:
    human = [
        _record("a", {"D1": "low", "D2": "unclear", "D3": "high", "D4": "low"}),
    ]
    pred = _out(
            _pred("a", {domain: "unclear" for domain in human[0].judgements}),
        )

    scores = grade_rob(pred, human)

    assert scores["domain_accuracy"] == 1 / 4
    assert scores["kappa"] == 0.0
    assert scores["reward"] == 0.0


def test_ordinal_weighting_halves_low_vs_high_error_when_moved_to_unclear() -> None:
    human = [
        _record("a", {"D1": "low", "D2": "unclear", "D3": "high", "D4": "high"}),
    ]
    low_for_high = _out(_pred("a", {"D1": "low", "D2": "unclear", "D3": "high", "D4": "low"}))
    unclear_for_high = _out(
            _pred("a", {"D1": "low", "D2": "unclear", "D3": "high", "D4": "unclear"})
        )

    low_scores = grade_rob(low_for_high, human)
    unclear_scores = grade_rob(unclear_for_high, human)

    # low-vs-high has observed disagreement 2/4 and expected disagreement 1.0.
    assert low_scores["kappa"] == pytest.approx(0.5)
    assert low_scores["reward"] == pytest.approx(0.5)
    # unclear-vs-high has observed disagreement 1/4: exactly half the polar miss.
    # With the changed prediction marginal, expected disagreement is 7/8.
    assert unclear_scores["kappa"] == pytest.approx(5 / 7)
    assert unclear_scores["reward"] == pytest.approx(5 / 7)
    assert unclear_scores["reward"] > low_scores["reward"]


def test_overall_bias_rows_are_diagnostic_only() -> None:
    human_without_overall = [
        _record("a", {"D1": "low", "D2": "high", "D3": "unclear"}),
    ]
    pred_without_overall = _out(_pred("a", {"D1": "low", "D2": "high", "D3": "unclear"}))
    human_with_overall = [
        _record("a", {"D1": "low", "D2": "high", "D3": "unclear", "Overall bias": "high"}),
    ]
    pred_with_wrong_overall = _out(
            _pred("a", {"D1": "low", "D2": "high", "D3": "unclear", "Overall bias": "low"})
        )

    base = grade_rob(pred_without_overall, human_without_overall)
    with_overall = grade_rob(pred_with_wrong_overall, human_with_overall)

    for key in ("reward", "kappa", "domain_accuracy", "n", "exact"):
        assert with_overall[key] == base[key]
    assert with_overall["overall_bias_n"] == 1
    assert with_overall["overall_bias_exact"] == 0
    assert with_overall["overall_bias_accuracy"] == 0.0


def test_oracle_with_overall_bias_predictions_still_scores_one() -> None:
    human = [
        _record("a", {"D1": "low", "D2": "high", "Overall bias": "unclear"}),
    ]
    pred = _out(
            _pred("a", {"D1": "low", "D2": "high", "Overall bias": "unclear"}),
        )

    scores = grade_rob(pred, human)

    assert scores["reward"] == 1.0
    assert scores["kappa"] == 1.0
    assert scores["overall_bias_n"] == 1
    assert scores["overall_bias_exact"] == 1
    assert scores["overall_bias_accuracy"] == 1.0


def test_reward_details_include_full_domain_matrix_and_ignored_predictions() -> None:
    human = [
        _record("a", {"D1": "high", "D2": "low", "Overall bias": "high"}),
        _record("b", {"D1": "unclear"}, outcome="Mortality"),
    ]
    pred = _out(
            _pred("a", {"D1": "unclear", "Overall bias": "low", "Extra": "high"}),
            _pred("b", {"D1": "unclear"}, outcome="Mortality"),
            _pred("extra", {"D1": "high"}),
        )

    scores = grade_rob(pred, human)
    details = build_details(pred, human, scores, review_id="T")

    assert details["task"] == "risk_of_bias"
    assert details["review_id"] == "T"
    domain_rows = [
        domain
        for record in details["records"]
        for domain in record["domains"]
    ]
    assert len(domain_rows) == 4
    by_key = {
        (row["study_id"], row["outcome"], row["domain"]): row
        for row in domain_rows
    }
    assert by_key[("a", None, "D1")] == {
        "study_id": "a",
        "outcome": None,
        "framework": "rob1",
        "domain": "D1",
        "expected": "high",
        "observed": "unclear",
        "scored_as": "unclear",
        "correct": False,
        "error_type": "label_mismatch",
        "is_high_reference": True,
        "high_predicted_not_low": True,
        "high_exact": False,
        "is_overall_bias": False,
        "graded": True,
    }
    assert by_key[("a", None, "D2")]["observed"] is None
    assert by_key[("a", None, "D2")]["scored_as"] == "low"
    assert by_key[("a", None, "D2")]["correct"] is True
    assert by_key[("a", None, "D2")]["error_type"] == "missing_judgement"
    assert by_key[("a", None, "D2")]["graded"] is True
    assert by_key[("a", None, "Overall bias")]["correct"] is False
    assert by_key[("a", None, "Overall bias")]["error_type"] == "label_mismatch"
    assert by_key[("a", None, "Overall bias")]["is_overall_bias"] is True
    assert by_key[("a", None, "Overall bias")]["graded"] is False
    assert by_key[("b", "Mortality", "D1")]["correct"] is True
    assert by_key[("b", "Mortality", "D1")]["graded"] is True
    assert {item["reason"] for item in details["ignored_predictions"]} == {
        "extra_domain",
        "extra_record",
    }
    assert all(error["domain"] != "Overall bias" for error in details["errors"])


def test_write_keeps_reward_json_numeric_and_writes_details(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    human = [_record("a", {"D1": "high"})]
    pred = _out(_pred("a", {"D1": "high"}))
    scores = grade_rob(pred, human)
    details = build_details(pred, human, scores, review_id="T")
    monkeypatch.setattr(G, "OUT", tmp_path)

    G._write(scores, float(scores["reward"]), details)

    reward = json.loads((tmp_path / "reward.json").read_text())
    reward_details = json.loads((tmp_path / "reward-details.json").read_text())
    assert reward["reward"] == 1.0
    assert "records" not in reward
    assert reward_details["records"] == details["records"]


def _run_main(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, answer: object) -> dict:
    human_dir, task_dir, out_dir = tmp_path / "human", tmp_path / "task", tmp_path / "out"
    human_dir.mkdir()
    task_dir.mkdir()
    (human_dir / "T.json").write_text(
        json.dumps(
            {
                "review_id": "T",
                "rob_human": [
                    {"study_id": "a", "outcome": None, "framework": "rob1", "judgements": {"D1": "high", "D2": "low"}},
                    {"study_id": "b", "outcome": "Mortality", "framework": "rob2", "judgements": {"D1": "unclear", "D2": "low"}},
                ],
            }
        )
    )
    (task_dir / "judgements.json").write_text(json.dumps(answer))
    monkeypatch.setattr(G, "HUMAN_DIR", human_dir)
    monkeypatch.setattr(G, "TASK", task_dir)
    monkeypatch.setattr(G, "OUT", out_dir)
    G.main()
    return json.loads((out_dir / "reward-details.json").read_text())


def test_nested_answer_keys_null_outcome_as_study_level(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    details = _run_main(
        tmp_path,
        monkeypatch,
        {
            "judgements": {
                "a": {"study-level": {"D1": "high", "D2": "low"}},
                "b": {"Mortality": {"D1": "unclear", "D2": "low"}},
            }
        },
    )

    assert details["status"] == "scored"
    assert details["metrics"]["reward"] == 1.0
    assert details["ignored_predictions"] == []


def test_answer_under_wrong_outcome_key_is_unmatched(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    details = _run_main(
        tmp_path,
        monkeypatch,
        {
            "judgements": {
                "a": {"null": {"D1": "high", "D2": "low"}},
                "b": {"mortality": {"D1": "unclear", "D2": "low"}},
            }
        },
    )

    assert details["metrics"]["reward"] == 0.0
    assert {(item["study_id"], item["outcome"], item["reason"]) for item in details["ignored_predictions"]} == {
        ("a", "null", "extra_record"),
        ("b", "mortality", "extra_record"),
    }


@pytest.mark.parametrize(
    "answer",
    [
        {"judgements": [{"study_id": "a", "outcome": None, "judgements": {"D1": "high", "D2": "low"}}]},
        {"judgements": {"a": {"study-level": {"D1": "High", "D2": "low"}}}},
        {"judgements": {"a": {"D1": "high", "D2": "low"}}},
        {"judgements": {}, "notes": "extra field"},
    ],
    ids=["old-list-shape", "bad-label", "missing-outcome-level", "extra-top-level-field"],
)
def test_malformed_answer_is_a_parse_error_scored_zero(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    answer: object,
) -> None:
    details = _run_main(tmp_path, monkeypatch, answer)

    assert details["status"] == "parse_error"
    assert details["metrics"]["reward"] == 0.0
