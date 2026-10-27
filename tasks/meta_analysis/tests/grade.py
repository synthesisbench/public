"""Verifier for the meta-analysis Harbor task.

Self-contained by design: the numeric logic is inlined here rather than imported,
so the verifier has no dependency on how instances are built. Human references are
discovered from /tests/gold, the
model answer is read from /task/analyses.json, and the reward is written to
/logs/verifier/reward.txt.

Reward = `point_and_ci_within_tol` = the point estimate and both 95% CI
endpoints reproduced within tolerance. Method/measure-label match, exact_method,
direction/significance `conclusion`, and i2_within_tol are SECONDARY diagnostics
— computed and reported, never the reward.
The agent picks its own effect-measure and model, so pred's log-ness comes from
pred's chosen measure and gold's from gold's measure.
"""

from __future__ import annotations

import json
import math
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from pydantic import BaseModel

# --------------------------------------------------------------------------- #
# log-vs-linear by effect measure.
# --------------------------------------------------------------------------- #

LOG_MEASURES = {
    "risk ratio", "odds ratio", "peto odds ratio", "hazard ratio",
    "rate ratio", "risk ratio (non-event)", "ratio of geometric means",
    "rr", "or", "hr", "irr",
}
DIFF_MEASURES = {
    "mean difference", "std mean difference", "std. mean difference",
    "standardized mean difference", "risk difference", "rate difference",
    "md", "smd", "rd",
}


def measure_is_log(effect_measure: str, log_scale_data: bool = True) -> bool:
    """Decide log-vs-linear by the effect measure's semantics, not the flag."""
    m = (effect_measure or "").strip().lower()
    if m in LOG_MEASURES:
        return True
    if m in DIFF_MEASURES:
        return False
    return log_scale_data


# --------------------------------------------------------------------------- #
# Numeric normalization.
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class Tol:
    """Tolerances for numeric comparison.

    point/CI tolerances are absolute in log space for ratio measures and relative
    for difference measures. i2 is absolute (percentage points).
    """

    rel: float = 0.05  # relative tolerance for difference-measure point/CI
    log_abs: float = 0.05  # absolute tolerance in log space for ratio measures
    i2: float = 5.0  # absolute tolerance for I^2 (percentage points)
    cont_abs: float = 1e-6  # absolute floor so exact values pass


def null_value(is_log: bool) -> float:
    """The no-effect value: 1.0 for ratio measures, 0.0 for differences."""
    return 1.0 if is_log else 0.0


def effect_sign(estimate: float, is_log: bool) -> int:
    """Direction of effect relative to the null. Returns -1, 0, or +1."""
    null = null_value(is_log)
    if math.isclose(estimate, null, rel_tol=0, abs_tol=1e-12):
        return 0
    return 1 if estimate > null else -1


def crosses_null(ci_low: float, ci_high: float, is_log: bool) -> bool:
    """Does the CI include the null value (i.e. non-significant)?"""
    null = null_value(is_log)
    lo, hi = sorted((ci_low, ci_high))
    return lo <= null <= hi


def within(pred: float, gold: float, tol: Tol, is_log: bool) -> bool:
    """Is a point estimate within tolerance of gold?"""
    if is_log:
        if pred <= 0 or gold <= 0:
            return False
        return abs(math.log(pred) - math.log(gold)) <= tol.log_abs
    denom = max(abs(gold), 1.0)
    return abs(pred - gold) <= max(tol.rel * denom, tol.cont_abs)


def ci_within(
    pred: tuple[float, float],
    gold: tuple[float, float],
    tol: Tol,
    is_log: bool,
) -> bool:
    """Both CI endpoints within tolerance."""
    return within(pred[0], gold[0], tol, is_log) and within(pred[1], gold[1], tol, is_log)


def i2_close(pred: Optional[float], gold: Optional[float], tol: Tol) -> bool:
    """I^2 within absolute tolerance. Both-missing counts as a match."""
    if pred is None and gold is None:
        return True
    if pred is None or gold is None:
        return False
    return abs(pred - gold) <= tol.i2


# --------------------------------------------------------------------------- #
# Contracts
# --------------------------------------------------------------------------- #


class Estimate(BaseModel):
    mean: float
    ci_start: float
    ci_end: float


class MetaOut(BaseModel):
    """One pooled estimate (agent output row or gold reference row)."""

    analysis_group: int
    analysis_id: int
    effect_measure: str
    analysis_model: str = ""
    log_scale_data: bool = True
    pooled: Estimate
    i_squared: Optional[float] = None  # 0..100

    @property
    def is_log(self) -> bool:
        return measure_is_log(self.effect_measure, self.log_scale_data)


class MetaOutDoc(BaseModel):
    analyses: list[MetaOut]


# --------------------------------------------------------------------------- #
# Per-analysis grade.
# --------------------------------------------------------------------------- #


def grade_meta(pred: MetaOut, gold: MetaOut, tol: Optional[Tol] = None) -> dict:
    """Grade one pooled meta-analysis estimate against gold.

    Each side's log-ness is derived from ITS OWN chosen measure: the agent may pick
    a different measure than gold, so direction/significance use pred.is_log for
    pred and gold.is_log for gold.
    """
    tol = tol or Tol()
    pred_log = pred.is_log
    gold_log = gold.is_log

    point_ok = within(pred.pooled.mean, gold.pooled.mean, tol, gold_log)
    ci_ok = ci_within(
        (pred.pooled.ci_start, pred.pooled.ci_end),
        (gold.pooled.ci_start, gold.pooled.ci_end),
        tol,
        gold_log,
    )
    i2_ok = i2_close(pred.i_squared, gold.i_squared, tol)

    direction_match = effect_sign(pred.pooled.mean, pred_log) == effect_sign(
        gold.pooled.mean, gold_log
    )
    pred_sig = not crosses_null(pred.pooled.ci_start, pred.pooled.ci_end, pred_log)
    gold_sig = not crosses_null(gold.pooled.ci_start, gold.pooled.ci_end, gold_log)
    significance_match = pred_sig == gold_sig

    method_match = pred.analysis_model.strip().lower() == gold.analysis_model.strip().lower()
    measure_match = pred.effect_measure.strip().lower() == gold.effect_measure.strip().lower()

    exact_method_reward = float(point_ok and ci_ok and method_match and measure_match)
    # Direction is only defined for a significant effect. When gold is
    # non-significant the clinical conclusion is "no effect" and a correct agent
    # need only agree on (non-)significance, regardless of which side of the null
    # its near-null point estimate happens to fall.
    conclusion_reward = float(
        significance_match and (direction_match or not gold_sig)
    )

    return {
        "point_within_tol": float(point_ok),
        "ci_within_tol": float(ci_ok),
        "point_and_ci_within_tol": float(point_ok and ci_ok),
        "i2_within_tol": float(i2_ok),
        "direction_match": float(direction_match),
        "significance_match": float(significance_match),
        "method_match": float(method_match),
        "measure_match": float(measure_match),
        "exact_method": exact_method_reward,
        "conclusion": conclusion_reward,
    }


SUBMETRICS = (
    "point_within_tol",
    "ci_within_tol",
    "point_and_ci_within_tol",
    "i2_within_tol",
    "direction_match",
    "significance_match",
    "method_match",
    "measure_match",
    "exact_method",
    "conclusion",
)


def _key(record: MetaOut) -> tuple[int, int]:
    return record.analysis_group, record.analysis_id


def grade(pred: MetaOutDoc, gold: list[MetaOut], tol: Optional[Tol] = None) -> dict:
    """Per-review reward = mean of per-analysis point+CI matches.

    A missing/omitted analysis in the agent output scores 0 for every sub-metric.
    """
    pred_by_key = {_key(record): record for record in pred.analyses}

    sums = {name: 0.0 for name in SUBMETRICS}
    n = len(gold)
    for gold_record in gold:
        pred_record = pred_by_key.get(_key(gold_record))
        if pred_record is None:
            continue
        scores = grade_meta(pred_record, gold_record, tol)
        for name in SUBMETRICS:
            sums[name] += scores[name]

    means = {name: (sums[name] / n if n else 0.0) for name in SUBMETRICS}
    return {**means, "n": n, "reward": means["point_and_ci_within_tol"]}


# --------------------------------------------------------------------------- #
# Verifier I/O
# --------------------------------------------------------------------------- #

GOLD_DIR = Path("/tests/gold")
TASK = Path("/task")
OUT = Path("/logs/verifier")


def _write(scores: dict, reward_value: float) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    numeric_scores = {
        key: float(value)
        for key, value in scores.items()
        if isinstance(value, (int, float))
    }
    (OUT / "reward.json").write_text(json.dumps(numeric_scores))
    (OUT / "reward.txt").write_text(str(reward_value))


def _load_gold() -> tuple[str, list[MetaOut]] | None:
    try:
        gold_path = next(iter(sorted(GOLD_DIR.glob("*.json"))))
    except StopIteration:
        return None
    raw = json.loads(gold_path.read_text())
    review_id = str(raw.get("review_id") or gold_path.stem)
    records = [MetaOut.model_validate(record) for record in raw["meta_human"]]
    return review_id, records


def main() -> int:
    try:
        loaded_gold = _load_gold()
    except Exception as exc:
        print(f"FAIL: failed to parse gold reference JSON under /tests/gold: {exc}")
        _write({"reward": 0.0}, 0.0)
        return 0

    if loaded_gold is None:
        print("FAIL: no gold reference JSON found under /tests/gold")
        _write({"reward": 0.0}, 0.0)
        return 0

    review_id, gold = loaded_gold
    answer_path = TASK / "analyses.json"
    if not answer_path.exists():
        print(f"WARN: {answer_path} missing")
        pred = MetaOutDoc(analyses=[])
    else:
        try:
            pred = MetaOutDoc.model_validate_json(answer_path.read_text())
        except Exception as exc:
            print(f"WARN: failed to parse {answer_path}: {exc}")
            pred = MetaOutDoc(analyses=[])

    try:
        scores = grade(pred, gold)
        reward_value = float(scores["reward"])
        _write(scores, reward_value)
        print(
            f"meta-analysis {review_id}: "
            f"reward={reward_value:.4f} exact_method={scores['exact_method']:.4f} "
            f"n={scores['n']}"
        )
    except Exception as exc:
        print(f"FAIL: failed to score {answer_path}: {exc}")
        _write({"reward": 0.0}, 0.0)
    return 0


if __name__ == "__main__":
    sys.exit(main())
