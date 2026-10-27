"""Verifier for the full-text screening Harbor task.

Runs inside the verifier. Human references are discovered from /tests/human, the model answer
is read from /task/decisions.json, and the reward is written to
/logs/verifier/reward.txt.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel

ScreenLabel = Literal["include", "exclude"]


class ScreenOut(BaseModel):
    decisions: dict[str, ScreenLabel]


class ScreenHuman(BaseModel):
    review_id: str
    include: dict[str, bool]


HUMAN_DIR = Path("/tests/human")
TASK = Path("/task")
OUT = Path("/logs/verifier")

# The primary reward is an asymmetric, chance-corrected disagreement score.
# A false negative costs ten times a false positive. Expected disagreement is
# derived from the human and predicted marginals, so either constant classifier
# scores zero instead of receiving a class-prevalence floor.
FALSE_NEGATIVE_COST = 10.0
FALSE_POSITIVE_COST = 1.0


def _fbeta(precision: float, recall: float, beta: float) -> float:
    """F_beta in [0,1]. 0 when either axis is 0; 1 only when both are 1."""
    b2 = beta * beta
    denom = b2 * precision + recall
    return (1 + b2) * precision * recall / denom if denom > 0 else 0.0


def _chance_corrected_reward(tp: int, fn: int, tn: int, fp: int) -> float:
    n = tp + fn + tn + fp
    if n == 0:
        return 1.0
    human_positive = tp + fn
    human_negative = tn + fp
    predicted_positive = tp + fp
    predicted_negative = tn + fn
    observed_cost = FALSE_NEGATIVE_COST * fn + FALSE_POSITIVE_COST * fp
    expected_cost = (
        FALSE_NEGATIVE_COST * human_positive * predicted_negative
        + FALSE_POSITIVE_COST * human_negative * predicted_positive
    ) / n
    if expected_cost == 0:
        return 1.0 if observed_cost == 0 else 0.0
    return max(0.0, 1.0 - observed_cost / expected_cost)


def _confusion(pred: ScreenOut, human: ScreenHuman) -> tuple[int, int, int, int]:
    tp = fn = tn = fp = 0
    for sid, is_include in human.include.items():
        included = pred.decisions.get(sid, "exclude") == "include"
        if is_include and included:
            tp += 1
        elif is_include and not included:
            fn += 1
        elif not is_include and included:
            fp += 1
        else:
            tn += 1
    return tp, fn, tn, fp


def _expected_label(is_include: bool) -> ScreenLabel:
    return "include" if is_include else "exclude"


def build_details(
    pred: ScreenOut,
    human: ScreenHuman | None,
    scores: dict[str, float | int],
    *,
    status: str = "scored",
    message: str | None = None,
) -> dict[str, Any]:
    numeric_scores = _numeric_scores(scores)
    details: dict[str, Any] = {
        "task": "full_text_screening",
        "status": status,
        "metrics": numeric_scores,
        "items": [],
        "errors": {
            "false_negatives": [],
            "false_positives": [],
            "missing_decisions": [],
            "extra_decisions": [],
        },
    }
    if message:
        details["message"] = message
    if human is None:
        details["review_id"] = None
        return details

    expected_ids = set(human.include)
    observed_ids = set(pred.decisions)
    details["review_id"] = human.review_id

    for study_id in sorted(expected_ids):
        expected = _expected_label(human.include[study_id])
        observed = pred.decisions.get(study_id)
        if observed is None:
            error_type = "missing_decision"
        elif observed == expected:
            error_type = None
        elif expected == "include":
            error_type = "false_negative"
        else:
            error_type = "false_positive"

        item = {
            "study_id": study_id,
            "expected": expected,
            "observed": observed,
            "correct": observed == expected,
            "error_type": error_type,
        }
        details["items"].append(item)
        if error_type == "false_negative":
            details["errors"]["false_negatives"].append(item)
        elif error_type == "false_positive":
            details["errors"]["false_positives"].append(item)
        elif error_type == "missing_decision":
            details["errors"]["missing_decisions"].append(item)

    for study_id in sorted(observed_ids - expected_ids):
        details["errors"]["extra_decisions"].append(
            {
                "study_id": study_id,
                "expected": None,
                "observed": pred.decisions[study_id],
                "correct": False,
                "error_type": "extra_decision",
            }
        )

    return details


def grade_screening(
    pred: ScreenOut,
    human: ScreenHuman,
    target_recall: float = 0.95,
) -> dict[str, float | int]:
    expected_ids = set(human.include)
    observed_ids = set(pred.decisions)
    missing_decisions = expected_ids - observed_ids
    extra_decisions = observed_ids - expected_ids
    if missing_decisions or extra_decisions:
        return {
            "recall": 0.0,
            "precision": 0.0,
            "f1": 0.0,
            "specificity": 0.0,
            "workload_reduction": 0.0,
            "wss95": -target_recall,
            "meets_recall_target": 0.0,
            "key_set_match": 0.0,
            "missing_decisions": len(missing_decisions),
            "extra_decisions": len(extra_decisions),
            "n": len(human.include),
            "tp": 0,
            "fn": 0,
            "tn": 0,
            "fp": 0,
            "reward": 0.0,
        }
    tp, fn, tn, fp = _confusion(pred, human)
    n = tp + fn + tn + fp
    recall = tp / (tp + fn) if (tp + fn) else 1.0
    precision = tp / (tp + fp) if (tp + fp) else 1.0
    f1 = _fbeta(precision, recall, 1.0)
    specificity = tn / (tn + fp) if (tn + fp) else 1.0
    workload_reduction = (tn + fn) / n if n else 0.0
    wss = workload_reduction - (1.0 - target_recall)
    meets = recall >= target_recall  # retained as a diagnostic only; no longer gates reward
    reward = _chance_corrected_reward(tp, fn, tn, fp)
    return {
        "recall": recall,
        "precision": precision,
        "f1": f1,
        "specificity": specificity,
        "workload_reduction": workload_reduction,
        "wss95": wss,
        "meets_recall_target": float(meets),
        "key_set_match": 1.0,
        "missing_decisions": 0,
        "extra_decisions": 0,
        "n": n,
        "tp": tp,
        "fn": fn,
        "tn": tn,
        "fp": fp,
        "reward": reward,
    }


def _numeric_scores(scores: dict[str, float | int]) -> dict[str, float]:
    return {
        key: float(value)
        for key, value in scores.items()
        if isinstance(value, (int, float))
    }


def _write(
    scores: dict[str, float | int],
    reward_value: float,
    details: dict[str, Any],
) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    numeric_scores = _numeric_scores(scores)
    (OUT / "reward.json").write_text(json.dumps(numeric_scores))
    (OUT / "reward-details.json").write_text(json.dumps(details, indent=2))
    (OUT / "reward.txt").write_text(str(reward_value))


def _load_human() -> ScreenHuman | None:
    try:
        human_path = next(iter(sorted(HUMAN_DIR.glob("*.json"))))
    except StopIteration:
        return None

    raw = json.loads(human_path.read_text())
    return ScreenHuman.model_validate(raw["screen_human"])


def main() -> int:
    human = _load_human()
    if human is None:
        print("FAIL: no human reference JSON found under /tests/human")
        scores = {"reward": 0.0}
        details = build_details(
            ScreenOut(decisions={}),
            None,
            scores,
            status="setup_error",
            message="no human reference JSON found under /tests/human",
        )
        _write(scores, 0.0, details)
        return 0

    answer_path = TASK / "decisions.json"
    if not answer_path.exists():
        print(f"FAIL: {answer_path} missing")
        pred = ScreenOut(decisions={})
        scores = grade_screening(pred, human)
        details = build_details(
            pred,
            human,
            scores,
            status="missing_output",
            message=f"{answer_path} missing",
        )
        _write(scores, 0.0, details)
        return 0

    status = "scored"
    message = None
    try:
        pred = ScreenOut.model_validate_json(answer_path.read_text())
    except Exception as exc:
        print(f"WARN: failed to parse {answer_path}: {exc}")
        pred = ScreenOut(decisions={})
        status = "parse_error"
        message = f"failed to parse {answer_path}: {exc}"

    scores = grade_screening(pred, human)
    reward_value = float(scores["reward"])
    details = build_details(pred, human, scores, status=status, message=message)
    _write(scores, reward_value, details)
    print(
        f"full-text screening {human.review_id}: "
        f"reward={reward_value:.4f} recall={scores['recall']:.4f} "
        f"specificity={scores['specificity']:.4f}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
