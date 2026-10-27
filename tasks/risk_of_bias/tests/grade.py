"""Verifier for the risk-of-bias Harbor task.

Runs inside the verifier. Human references are discovered from /tests/human, the model answer
is read from /task/judgements.json, and the reward is written to
/logs/verifier/reward.txt.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict

RobLabel = Literal["low", "unclear", "high"]
Framework = Literal["rob1", "rob2"]
# The outcome key for a task whose outcome is null (a study-level RoB 1 judgement).
STUDY_LEVEL = "study-level"


class RobOut(BaseModel):
    """{"judgements": {study_id: {outcome: {domain: label}}}}."""

    model_config = ConfigDict(extra="forbid")

    judgements: dict[str, dict[str, dict[str, RobLabel]]]


class RobHumanRecord(BaseModel):
    study_id: str
    outcome: str | None = None
    framework: Framework
    judgements: dict[str, RobLabel]

    @property
    def outcome_key(self) -> str:
        return STUDY_LEVEL if self.outcome is None else self.outcome


HUMAN_DIR = Path("/tests/human")
TASK = Path("/task")
OUT = Path("/logs/verifier")


def _predicted(pred: RobOut, record: RobHumanRecord) -> dict[str, RobLabel]:
    return pred.judgements.get(record.study_id, {}).get(record.outcome_key, {})


def build_details(
    pred: RobOut,
    human: list[RobHumanRecord],
    scores: dict[str, float | int],
    *,
    review_id: str | None = None,
    status: str = "scored",
    message: str | None = None,
) -> dict[str, Any]:
    human_by_key = {(record.study_id, record.outcome_key): record for record in human}
    records: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []

    for human_record in human:
        pred_judgements = _predicted(pred, human_record)
        domain_rows: list[dict[str, Any]] = []

        for domain in sorted(human_record.judgements):
            expected = human_record.judgements[domain]
            observed = pred_judgements.get(domain)
            scored_as = observed if observed is not None else "low"
            correct = scored_as == expected
            if observed is None:
                error_type = "missing_judgement"
            elif correct:
                error_type = None
            else:
                error_type = "label_mismatch"

            row = {
                "study_id": human_record.study_id,
                "outcome": human_record.outcome,
                "framework": human_record.framework,
                "domain": domain,
                "expected": expected,
                "observed": observed,
                "scored_as": scored_as,
                "correct": correct,
                "error_type": error_type,
                "is_high_reference": expected == "high",
                "high_predicted_not_low": expected == "high" and scored_as != "low",
                "high_exact": expected == "high" and scored_as == "high",
                "is_overall_bias": domain == "Overall bias",
                "graded": domain != "Overall bias",
            }
            domain_rows.append(row)
            if row["graded"] and error_type is not None:
                errors.append(row)

        records.append(
            {
                "study_id": human_record.study_id,
                "outcome": human_record.outcome,
                "framework": human_record.framework,
                "domains": domain_rows,
            }
        )

    ignored_predictions: list[dict[str, Any]] = []
    for study_id, outcomes in pred.judgements.items():
        for outcome, pred_judgements in outcomes.items():
            human_record = human_by_key.get((study_id, outcome))
            if human_record is None:
                ignored_predictions.append(
                    {
                        "study_id": study_id,
                        "outcome": outcome,
                        "reason": "extra_record",
                        "judgements": dict(sorted(pred_judgements.items())),
                    }
                )
                continue
            for domain in sorted(set(pred_judgements) - set(human_record.judgements)):
                ignored_predictions.append(
                    {
                        "study_id": study_id,
                        "outcome": outcome,
                        "reason": "extra_domain",
                        "domain": domain,
                        "observed": pred_judgements[domain],
                    }
                )

    details: dict[str, Any] = {
        "task": "risk_of_bias",
        "review_id": review_id,
        "status": status,
        "metrics": _numeric_scores(scores),
        "records": records,
        "errors": errors,
        "ignored_predictions": ignored_predictions,
    }
    if message:
        details["message"] = message
    return details


def grade_rob(pred: RobOut, human: list[RobHumanRecord]) -> dict[str, float | int]:
    label_idx: dict[RobLabel, int] = {"low": 0, "unclear": 1, "high": 2}
    pred_counts = dict.fromkeys(label_idx, 0)
    gold_counts = dict.fromkeys(label_idx, 0)
    observed_disagreement = 0

    total = 0
    exact = 0
    high_total = 0
    high_not_low = 0
    high_exact = 0
    overall_total = 0
    overall_exact = 0

    for human_record in human:
        pred_judgements = _predicted(pred, human_record)

        for domain, human_label in human_record.judgements.items():
            pred_label = pred_judgements.get(domain, "low")
            if domain == "Overall bias":
                overall_total += 1
                overall_exact += int(pred_label == human_label)
                continue

            total += 1
            exact += int(pred_label == human_label)
            pred_counts[pred_label] += 1
            gold_counts[human_label] += 1
            observed_disagreement += abs(label_idx[pred_label] - label_idx[human_label])

            if human_label == "high":
                high_total += 1
                high_not_low += int(pred_label != "low")
                high_exact += int(pred_label == "high")

    domain_accuracy = exact / total if total else 0.0
    high_risk_recall = high_not_low / high_total if high_total else 1.0
    high_exact_recall = high_exact / high_total if high_total else 1.0
    overall_bias_accuracy = (
        overall_exact / overall_total if overall_total else 0.0
    )
    # Reward per-judgement agreement with the review authors using linearly weighted
    # Cohen's kappa: any constant guess (all-low, all-unclear, or an empty file) scores 0, while
    # directional errors cost half of polar errors. "Overall bias" is excluded because it
    # is the review authors' holistic judgement, not mechanically derivable from the
    # component domains: identical component profiles can map to different Overall labels.
    if total:
        expected_disagreement = 0
        for pred_label, pred_count in pred_counts.items():
            for gold_label, gold_count in gold_counts.items():
                expected_disagreement += (
                    pred_count
                    * gold_count
                    * abs(label_idx[pred_label] - label_idx[gold_label])
                )
        if expected_disagreement == 0:
            kappa = 1.0 if observed_disagreement == 0 else 0.0
        else:
            kappa = 1 - (observed_disagreement * total) / expected_disagreement
    else:
        kappa = 0.0
    reward = max(0.0, kappa)

    return {
        "reward": reward,
        "kappa": kappa,
        "domain_accuracy": domain_accuracy,
        "n": total,
        "exact": exact,
        "overall_bias_n": overall_total,
        "overall_bias_exact": overall_exact,
        "overall_bias_accuracy": overall_bias_accuracy,
        "high_total": high_total,
        "high_exact": high_exact,
        "high_exact_recall": high_exact_recall,
        "high_risk_recall": high_risk_recall,
        "high_not_low": high_not_low,
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


def _load_human() -> tuple[str, list[RobHumanRecord]] | None:
    try:
        human_path = next(iter(sorted(HUMAN_DIR.glob("*.json"))))
    except StopIteration:
        return None

    raw = json.loads(human_path.read_text())
    review_id = str(raw.get("review_id") or human_path.stem)
    records = [RobHumanRecord.model_validate(record) for record in raw["rob_human"]]
    return review_id, records


def main() -> int:
    try:
        loaded_human = _load_human()
    except Exception as exc:
        print(f"FAIL: failed to parse human reference JSON under /tests/human: {exc}")
        scores = {"reward": 0.0}
        details = build_details(
            RobOut(judgements={}),
            [],
            scores,
            status="setup_error",
            message=f"failed to parse human reference JSON under /tests/human: {exc}",
        )
        _write(scores, 0.0, details)
        return 0

    if loaded_human is None:
        print("FAIL: no human reference JSON found under /tests/human")
        scores = {"reward": 0.0}
        details = build_details(
            RobOut(judgements={}),
            [],
            scores,
            status="setup_error",
            message="no human reference JSON found under /tests/human",
        )
        _write(scores, 0.0, details)
        return 0

    review_id, human = loaded_human
    answer_path = TASK / "judgements.json"
    status = "scored"
    message = None
    if not answer_path.exists():
        print(f"WARN: {answer_path} missing")
        pred = RobOut(judgements={})
        status = "missing_output"
        message = f"{answer_path} missing"
    else:
        try:
            pred = RobOut.model_validate_json(answer_path.read_text())
        except Exception as exc:
            print(f"WARN: failed to parse {answer_path}: {exc}")
            pred = RobOut(judgements={})
            status = "parse_error"
            message = f"failed to parse {answer_path}: {exc}"

    try:
        scores = grade_rob(pred, human)
        reward_value = float(scores["reward"])
        details = build_details(
            pred,
            human,
            scores,
            review_id=review_id,
            status=status,
            message=message,
        )
        _write(scores, reward_value, details)
        print(
            f"risk-of-bias {review_id}: "
            f"reward={reward_value:.4f} kappa={scores['kappa']:.4f} "
            f"domain_accuracy={scores['domain_accuracy']:.4f} "
            f"high_risk_recall={scores['high_risk_recall']:.4f}"
        )
    except Exception as exc:
        print(f"FAIL: failed to score {answer_path}: {exc}")
        scores = {"reward": 0.0}
        details = build_details(
            pred,
            human,
            scores,
            review_id=review_id,
            status="scoring_error",
            message=f"failed to score {answer_path}: {exc}",
        )
        _write(scores, 0.0, details)
    return 0


if __name__ == "__main__":
    sys.exit(main())
