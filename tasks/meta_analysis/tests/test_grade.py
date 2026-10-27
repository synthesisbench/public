# Behavior manifest:
# - significant/non-significant split: test_oracle_perfect_replay_scores_reward_and_exact_method,
#   test_non_significant_gold_matched_by_non_significant_pred
# - ratio + difference measures: test_oracle_perfect_replay_scores_reward_and_exact_method,
#   test_non_significant_gold_does_not_require_direction
# - omitted-analysis averaging: test_omitted_analysis_is_penalized
# - group-key collision: test_collision_resolved_by_group_key
# - oracle perfect replay: test_oracle_perfect_replay_scores_reward_and_exact_method

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("meta_analysis_grade", HERE / "grade.py")
G = importlib.util.module_from_spec(spec)
sys.modules["meta_analysis_grade"] = G
assert spec.loader is not None
spec.loader.exec_module(G)

MetaOut = G.MetaOut
MetaOutDoc = G.MetaOutDoc
grade = G.grade


def _out(
    analysis_group: int,
    analysis_id: int,
    effect_measure: str,
    mean: float,
    ci_start: float,
    ci_end: float,
    analysis_model: str = "Random effect",
    i_squared: float | None = 0.0,
) -> MetaOut:
    return MetaOut(
        analysis_group=analysis_group,
        analysis_id=analysis_id,
        effect_measure=effect_measure,
        analysis_model=analysis_model,
        pooled={"mean": mean, "ci_start": ci_start, "ci_end": ci_end},
        i_squared=i_squared,
    )


# Synthetic DEMO-REVIEW arm rows: Study A 40/100 vs 20/100, Study B 30/80
# vs 16/80, and Study C 25/70 vs 14/70. MH-centered DL gives tau^2 = 0;
# random-effects inverse-variance pooling gives RR 1.8999 [1.4156, 2.5499].
_GOLD_SIG = _out(
    10,
    1,
    "Risk Ratio",
    1.899867720280963,
    1.415570350749751,
    2.5498537410407245,
)

# Synthetic DEMO-REVIEW arm rows: Study D 20/100 vs 18/100, Study E 12/80
# vs 14/80, and Study F 16/90 vs 15/90. The same method gives a
# non-significant RR 1.0228 [0.7096, 1.4741].
_GOLD_NONSIG = _out(
    10,
    2,
    "Risk Ratio",
    1.0227636557369564,
    0.7095936407912323,
    1.4741472236561064,
)

# Synthetic continuous rows: Study G has 10.0 (SD 4.0, n=50) in both arms;
# Study H has 12.0 (SD 5.0, n=40) in both arms. Fixed inverse-variance pooling
# gives MD 0.0 [-1.2752, 1.2752].
_GOLD_MD_NULL = _out(
    30,
    1,
    "Mean Difference",
    0.0,
    -1.2751760953194167,
    1.2751760953194167,
)


def test_oracle_perfect_replay_scores_reward_and_exact_method() -> None:
    gold = [_GOLD_SIG]
    pred = MetaOutDoc(analyses=[_GOLD_SIG.model_copy()])

    scores = grade(pred, gold)

    assert scores["reward"] == 1.0
    assert scores["conclusion"] == 1.0
    assert scores["exact_method"] == 1.0


def test_protective_estimate_misses_ci_reward() -> None:
    gold = [_GOLD_SIG]
    # Same measure, but the effect flips to the protective side (RR < 1, significant).
    # The CI is nowhere near gold's, so the reward is 0.0; the wrong direction
    # is also recorded as a diagnostic.
    pred = MetaOutDoc(
        analyses=[_out(10, 1, "Risk Ratio", 0.69, 0.52, 0.91)]
    )

    scores = grade(pred, gold)

    assert scores["direction_match"] == 0.0
    assert scores["ci_within_tol"] == 0.0
    assert scores["reward"] == 0.0


def test_gold_ci_with_wrong_point_estimate_misses_reward() -> None:
    gold = [_GOLD_SIG]
    pred = MetaOutDoc(
        analyses=[
            _out(
                10,
                1,
                "Risk Ratio",
                999.0,
                _GOLD_SIG.pooled.ci_start,
                _GOLD_SIG.pooled.ci_end,
            )
        ]
    )

    scores = grade(pred, gold)

    assert scores["point_within_tol"] == 0.0
    assert scores["ci_within_tol"] == 1.0
    assert scores["point_and_ci_within_tol"] == 0.0
    assert scores["reward"] == 0.0


def test_same_conclusion_wrong_numbers_misses_ci_reward() -> None:
    gold = [_GOLD_SIG]
    # Agent chose Odds Ratio (also a ratio measure) + a fixed-effect model. Direction
    # (>1) and significance (CI excludes 1) match gold, so the `conclusion` diagnostic
    # is 1.0 — but the CI is off, so the reward is 0.0. A model that
    # nails the broad conclusion without reproducing the pooled CI gets no reward credit.
    pred = MetaOutDoc(
        analyses=[
            _out(
                10,
                1,
                "Odds Ratio",
                1.62,
                1.12,
                2.34,
                analysis_model="Fixed effect",
            )
        ]
    )

    scores = grade(pred, gold)

    assert scores["conclusion"] == 1.0
    assert scores["ci_within_tol"] == 0.0
    assert scores["reward"] == 0.0
    assert scores["exact_method"] == 0.0
    assert scores["measure_match"] == 0.0
    assert scores["method_match"] == 0.0


def test_non_significant_gold_matched_by_non_significant_pred() -> None:
    # Gold CI crosses the null (RR 1.0228 [0.7096, 1.4741], non-significant).
    gold = [_GOLD_NONSIG]
    # Pred also non-significant and same direction (>1).
    pred = MetaOutDoc(
        analyses=[_out(10, 2, "Risk Ratio", 1.04, 0.72, 1.45)]
    )

    scores = grade(pred, gold)

    assert scores["significance_match"] == 1.0
    assert scores["direction_match"] == 1.0
    assert scores["reward"] == 1.0


def test_non_significant_gold_does_not_require_direction() -> None:
    # Gold sits exactly at the null (MD 0.0 [-1.2752, 1.2752], non-significant) — its
    # direction is undefined. A correct, non-significant pred on the OPPOSITE side
    # of the null must still score conclusion 1.0 (direction is irrelevant here).
    gold = [_GOLD_MD_NULL]
    pred = MetaOutDoc(
        analyses=[_out(30, 1, "Mean Difference", -0.3, -0.9, 0.8, i_squared=0.0)]
    )

    scores = grade(pred, gold)

    assert scores["significance_match"] == 1.0
    assert scores["direction_match"] == 0.0  # sign(-0.3) != sign(0.0)
    assert scores["conclusion"] == 1.0
    # Reward is `point_and_ci_within_tol`; this loose CI misses it even though the
    # `conclusion` diagnostic is satisfied.
    assert scores["reward"] == 0.0


def test_omitted_analysis_is_penalized() -> None:
    gold = [
        _GOLD_SIG,
        _GOLD_NONSIG,
    ]
    # Only the first analysis is answered; analysis (10, 2) is omitted -> scores 0.
    pred = MetaOutDoc(analyses=[_GOLD_SIG.model_copy()])

    scores = grade(pred, gold)

    assert scores["n"] == 2
    assert scores["reward"] == 0.5
    assert scores["conclusion"] == 0.5


def test_collision_resolved_by_group_key() -> None:
    # Same analysis_id, different group, different conclusions: the (group, id)
    # key must keep them distinct (the whole point of threading analysis_group).
    gold = [
        _GOLD_SIG.model_copy(update={"analysis_group": 10, "analysis_id": 7}),
        _GOLD_NONSIG.model_copy(update={"analysis_group": 20, "analysis_id": 7}),
    ]
    pred = MetaOutDoc(
        analyses=[
            gold[0].model_copy(),  # matches group 10
            gold[1].model_copy(),  # matches group 20
        ]
    )

    scores = grade(pred, gold)

    # Both keys threaded to the right gold row -> point+CI reward 1.0.
    assert scores["reward"] == 1.0
    assert scores["significance_match"] == 1.0
