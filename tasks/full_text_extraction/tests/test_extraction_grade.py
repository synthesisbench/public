# Behavior manifest:
# - Conventional F1: extras lower precision and reward,
#   test_inv2_extras_reduce_precision_and_f1_reward
# - Outcome-routing collisions: test_value_collision_uses_outcome_synonyms_as_tiebreaker
# - Multi-population recovery: test_two_denominators_one_arm_differs_recovers,
#   test_continuous_population_candidates_recover
# - Duplicate tuple/multiplicity: test_duplicate_value_tuples_remain_distinct_rows,
#   test_event_multiplicity_requires_token_distinct_pred_rows
# - Contradiction-vs-omission floors: test_inv5_at_n5, test_inv5_at_n40
# - Extract-nothing floor: test_emit_nothing_scores_zero_against_fact_model

"""Reward unit tests for the full-text extraction verifier (R3 gated-dock matcher).

Run: uv run pytest tasks/full_text_extraction/tests/test_extraction_grade.py
(also importable under pytest; each test_* is a plain assert function)

Loads this task's grade.py by path (importlib) under a UNIQUE module name so it
never collides with another Harbor task's grade.py in a single pytest session,
and so we exercise the real verifier module the harness executes, not a copy.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("extraction_grade", HERE / "grade.py")
G = importlib.util.module_from_spec(spec)
sys.modules["extraction_grade"] = G  # dataclass resolution needs the module registered
spec.loader.exec_module(G)

ArmRow = G.ArmRow
GoldFact = G.GoldFact
grade = G.grade_extraction
TAU = 0.95


def F(
    study,
    outcome,
    ee,
    et,
    ce,
    ct,
    *,
    slots=None,
    kind="plain",
    detail_labels=None,
    multiplicity=1,
):
    return GoldFact(
        study_id=study,
        canonical_outcome=outcome,
        data_type="dichotomous",
        values={
            "experimental_events": ee,
            "experimental_n": et,
            "control_events": ce,
            "control_n": ct,
        },
        slots=slots or [],
        kind=kind,
        detail_labels=detail_labels or [],
        multiplicity=multiplicity,
    )


def P(
    study,
    outcome,
    ee,
    et,
    ce,
    ct,
    *,
    breakout="",
    event="",
    subgroup="",
    analysis_group=None,
    analysis_id=None,
):
    return ArmRow(
        study_id=study,
        outcome=outcome,
        data_type="dichotomous",
        breakout=breakout,
        event=event,
        subgroup=subgroup,
        analysis_group=analysis_group,
        analysis_id=analysis_id,
        experimental_events=ee,
        experimental_n=et,
        control_events=ce,
        control_n=ct,
    )


def D(
    study,
    ee,
    et,
    ce,
    ct,
    subgroup="",
    analysis_name="",
    analysis_group=1,
    analysis_id=1,
):
    return ArmRow(
        study_id=study,
        analysis_group=analysis_group,
        analysis_id=analysis_id,
        data_type="dichotomous",
        subgroup=subgroup,
        analysis_name=analysis_name,
        experimental_events=ee,
        experimental_n=et,
        control_events=ce,
        control_n=ct,
    )


def C(
    study,
    em,
    esd,
    en,
    cm,
    csd,
    cn,
    subgroup="",
    analysis_name="",
    analysis_group=1,
    analysis_id=1,
):
    return ArmRow(
        study_id=study,
        analysis_group=analysis_group,
        analysis_id=analysis_id,
        data_type="continuous",
        subgroup=subgroup,
        analysis_name=analysis_name,
        experimental_mean=em,
        experimental_sd=esd,
        experimental_n=en,
        control_mean=cm,
        control_sd=csd,
        control_n=cn,
    )


def n_distinct_human(n):
    """N studies, each one distinct dichotomous quartet (no within-study dups)."""
    return [D(f"S{i}", 10 + i, 100 + i, 20 + i, 200 + i) for i in range(n)]


# --- INV1 oracle ----------------------------------------------------------


def test_inv1_oracle():
    human = [
        D("A", 8, 321, 9, 295),
        D("B", 39, 63, 30, 66),
        D("C", 17, 165, 22, 164),
    ]
    s = grade(human, human)
    assert s["reward"] == 1.0, s
    assert s["recovered"] == 3 and s["contradicted"] == 0 and s["missing"] == 0, s
    print(f"[PASS] INV1 oracle human->human == 1.0  reward={s['reward']}")


# --- INV2 extras are false positives -------------------------------------


def test_inv2_extras_reduce_precision_and_f1_reward():
    human = [D("A", 8, 321, 9, 295), D("B", 39, 63, 30, 66)]
    extras = [
        D("A", 1, 50, 2, 60),
        D("C", 5, 80, 6, 90),
        D("B", 11, 22, 33, 44),
    ]
    s = grade(human + extras, human)
    assert s["precision"] == pytest.approx(2 / 5), s
    assert s["recall"] == 1.0, s
    assert s["tp"] == 2 and s["fp"] == 3 and s["fn"] == 0, s
    assert s["contradicted"] == 0 and s["extras"] == 3, s
    assert s["reward"] == pytest.approx(4 / 7), s
    print(
        f"[PASS] INV2 extras penalized  reward={s['reward']:.4f} extras={s['extras']} contradicted={s['contradicted']}"
    )


def test_inv2_crux_same_arm_second_outcome():
    """Same randomized arms, different outcome -> extra, not a contradiction."""
    human = [D("A", 8, 321, 9, 295)]
    second_outcome = D("A", 3, 321, 4, 295, analysis_group=1, analysis_id=2)
    s = grade(human + [second_outcome], human)
    # Different outcome, same arms -> an extra (not a contradiction), so FP.
    assert s["contradicted"] == 0 and s["extras"] == 1, s
    assert s["precision"] == pytest.approx(1 / 2), s
    assert s["reward"] == pytest.approx(2 / 3), s
    print(
        f"[PASS] INV2-crux same-arm 2nd outcome -> penalized extra  extras={s['extras']} contradicted={s['contradicted']}"
    )


def test_exact_value_under_different_slot_still_recovers() -> None:
    human = [
        F(
            "A",
            "mortality",
            8,
            321,
            9,
            295,
            slots=[{"analysis_group": 1, "analysis_id": 1, "subgroup": "Female"}],
        )
    ]
    pred = [
        P(
            "A",
            "mortality",
            8,
            321,
            9,
            295,
            subgroup="Male",
            analysis_group=99,
            analysis_id=7,
        )
    ]

    match = G.match_rows(pred, human, {}, G.Tol())
    s = grade(pred, human)

    assert match.recovered == 1, match
    assert s["recovered"] == 1, s
    assert s["missing"] == 0, s
    assert s["extras"] == 0, s
    assert s["reward"] == 1.0, s


def test_repeated_outcome_names_recover_by_values_within_canonical_outcome() -> None:
    human = [
        F("A", "mortality", 8, 321, 9, 295),
        F("A", "mortality", 3, 100, 4, 101),
    ]
    pred = [
        P("A", "mortality", 8, 321, 9, 295),
        P("A", "mortality", 3, 100, 4, 101),
    ]

    s = grade(pred, human)

    assert s["reward"] == 1.0, s
    assert s["recovered"] == 2, s


def test_bare_outcome_name_recovers_across_multiple_canonicals_by_value() -> None:
    human = [
        F(
            "Ashford 2011",
            "prototype A vs prototype B | checkpoint one | Signal events",
            11,
            43,
            13,
            47,
        ),
        F(
            "Ashford 2011",
            "prototype A vs prototype B | checkpoint two | Signal events",
            4,
            39,
            8,
            41,
        ),
    ]
    pred = [
        P("Ashford 2011", "Signal events", 11, 43, 13, 47),
        P("Ashford 2011", "Signal events", 4, 39, 8, 41),
    ]
    vocab = {
        "review_id": "DEMO-REVIEW",
        "outcomes": [
            {
                "canonical": "prototype A vs prototype B | checkpoint one | Signal events",
                "members": [[1, 1]],
                "synonyms": ["Signal events"],
            },
            {
                "canonical": "prototype A vs prototype B | checkpoint two | Signal events",
                "members": [[10, 1]],
                "synonyms": ["Signal events"],
            },
        ],
        "labels": [],
    }

    s = grade(pred, human, vocab=vocab)

    assert s["reward"] == 1.0, s
    assert s["recovered"] == 2, s
    assert s["extras"] == 0, s
    assert s["missing"] == 0, s


def test_value_collision_uses_outcome_synonyms_as_tiebreaker() -> None:
    human = [
        F(
            "Bexley 2014",
            "prototype A vs prototype B | checkpoint one | Signal events",
            6,
            44,
            9,
            46,
        ),
        F(
            "Bexley 2014",
            "prototype A vs prototype B | checkpoint two | Signal events",
            6,
            44,
            9,
            46,
        ),
    ]
    vocab = {
        "review_id": "DEMO-REVIEW",
        "outcomes": [
            {
                "canonical": "prototype A vs prototype B | checkpoint one | Signal events",
                "members": [[1, 1]],
                "synonyms": ["checkpoint one signal"],
            },
            {
                "canonical": "prototype A vs prototype B | checkpoint two | Signal events",
                "members": [[10, 1]],
                "synonyms": ["checkpoint two signal"],
            },
        ],
        "labels": [],
    }
    pred = [
        P("Bexley 2014", "checkpoint one signal", 6, 44, 9, 46),
        P("Bexley 2014", "checkpoint two signal", 6, 44, 9, 46),
    ]
    single = [P("Bexley 2014", "checkpoint one signal", 6, 44, 9, 46)]

    s = grade(pred, human, vocab=vocab)
    one = grade(single, human, vocab=vocab)

    assert s["reward"] == 1.0, s
    assert s["recovered"] == 2, s
    assert s["missing"] == 0, s
    assert one["recovered"] == 1, one
    assert one["missing"] == 1, one
    assert one["extras"] == 0, one


def test_oracle_exact_values_with_bare_outcome_names_scores_one() -> None:
    human = [
        F(
            "Calder 2016",
            "prototype A vs prototype B | checkpoint one | Signal events",
            11,
            43,
            13,
            47,
        ),
        F(
            "Calder 2016",
            "prototype A vs prototype B | checkpoint two | Signal events",
            4,
            39,
            8,
            41,
        ),
        F(
            "Calder 2016",
            "prototype C vs prototype D | checkpoint one | Signal events",
            3,
            35,
            6,
            37,
        ),
    ]
    pred = [
        P(
            fact.study_id,
            fact.canonical_outcome.split("|")[-1].strip(),
            fact.values["experimental_events"],
            fact.values["experimental_n"],
            fact.values["control_events"],
            fact.values["control_n"],
        )
        for fact in human
    ]
    vocab = {
        "review_id": "DEMO-REVIEW",
        "outcomes": [
            {
                "canonical": fact.canonical_outcome,
                "members": [[index + 1, 1]],
                "synonyms": [fact.canonical_outcome.split("|")[-1].strip()],
            }
            for index, fact in enumerate(human)
        ],
        "labels": [],
    }

    s = grade(pred, human, vocab=vocab)

    assert s["reward"] == 1.0, s
    assert s["recovered"] == len(human), s
    assert s["extras"] == 0, s


def test_one_off_wrong_number_is_not_recovered() -> None:
    human = [
        F("A", "mortality", 8, 321, 9, 295),
        F("B", "mortality", 3, 100, 4, 101),
    ]
    pred = [
        P("A", "mortality", 8, 321, 9, 295),
        P("B", "mortality", 3, 100, 5, 101),
    ]

    s = grade(pred, human)

    assert s["recovered"] == 1, s
    assert s["contradicted"] == 1, s
    assert s["extras"] == 0, s
    assert s["precision"] == 1 / 2, s
    assert s["reward"] == pytest.approx(1 / 2), s


# --- INV4 missing is a false negative ------------------------------------


def test_inv4_missing_mild():
    human = [D("A", 8, 321, 9, 295), D("B", 39, 63, 30, 66), D("C", 17, 165, 22, 164)]
    pred = human[:2]  # drop one human row entirely; no contradiction
    s = grade(pred, human)
    assert s["precision"] == 1.0, s
    assert s["contradicted"] == 0 and s["missing"] == 1, s
    assert s["tp"] == 2 and s["fp"] == 0 and s["fn"] == 1, s
    assert s["recall"] == pytest.approx(2 / 3), s
    assert s["coverage"] == 2 / 3, s
    assert s["reward"] == pytest.approx(4 / 5) and s["reward"] > 0.5, s
    print(
        f"[PASS] INV4 missing-mild reward high  reward={s['reward']:.4f} missing={s['missing']}"
    )


# --- INV5 relative property at N=5 and N=40 -------------------------------


def _one_contradiction(n):
    human = n_distinct_human(n)
    pred = list(human)
    # mutate exactly ONE cell of the FIRST human row -> all-but-one -> contradiction
    bad = D(
        "S0",
        human[0].experimental_events,
        human[0].experimental_n,
        human[0].control_events + 7,
        human[0].control_n,
    )
    pred[0] = bad
    return grade(pred, human)


def _one_omission(n):
    human = n_distinct_human(n)
    pred = human[1:]  # drop one
    return grade(pred, human)


def test_inv5_at_n5():
    n = 5
    contra = _one_contradiction(n)
    omit = _one_omission(n)
    assert contra["contradicted"] == 1 and contra["recovered"] == n - 1, contra
    assert omit["contradicted"] == 0 and omit["missing"] == 1, omit
    assert contra["tp"] == n - 1 and contra["fp"] == 1 and contra["fn"] == 1, contra
    assert omit["tp"] == n - 1 and omit["fp"] == 0 and omit["fn"] == 1, omit
    assert contra["reward"] < omit["reward"], (contra["reward"], omit["reward"])
    print(
        f"[PASS] INV5 N=5  contra={contra['reward']:.4f} < omit={omit['reward']:.4f}"
    )


def test_inv5_at_n40():
    n = 40
    contra = _one_contradiction(n)
    omit = _one_omission(n)
    assert contra["contradicted"] == 1 and contra["recovered"] == n - 1, contra
    assert omit["contradicted"] == 0 and omit["missing"] == 1, omit
    assert contra["tp"] == n - 1 and contra["fp"] == 1 and contra["fn"] == 1, contra
    assert omit["tp"] == n - 1 and omit["fp"] == 0 and omit["fn"] == 1, omit
    assert contra["reward"] < omit["reward"], (contra["reward"], omit["reward"])
    print(
        f"[PASS] INV5 N=40  contra={contra['reward']:.4f} < omit={omit['reward']:.4f}"
    )


def test_one_contradiction_scores_worse_than_one_extra():
    human = n_distinct_human(10)
    with_extra = grade([*human, D("extra", 1, 10, 2, 10)], human)
    with_contradiction = _one_contradiction(10)

    assert with_extra["extras"] == 1 and with_extra["contradicted"] == 0, with_extra
    assert (
        with_contradiction["extras"] == 0 and with_contradiction["contradicted"] == 1
    ), with_contradiction
    assert with_contradiction["precision"] == 9 / 10, with_contradiction
    assert with_contradiction["reward"] < with_extra["reward"], (
        with_contradiction,
        with_extra,
    )


# --- near-miss contradiction (small N -> negative via gate) ---------------


def test_near_miss_contradiction_small_n_negative():
    human = [D("A", 8, 321, 9, 295), D("B", 39, 63, 30, 66), D("C", 17, 165, 22, 164)]
    pred = list(human)
    pred[0] = D("A", 8, 321, 99, 295)  # one cell wrong -> contradiction
    s = grade(pred, human)
    assert s["contradicted"] == 1 and s["recovered"] == 2, s
    assert s["reward"] == pytest.approx(2 / 3), s
    omit = grade(human[1:], human)
    assert s["reward"] < omit["reward"], (s["reward"], omit["reward"])
    print(
        f"[PASS] near-miss N=3 contradiction < omission  contra={s['reward']:.4f} omit={omit['reward']:.4f}"
    )


# --- continuous tolerance (D5) --------------------------------------------


def test_continuous_tolerance_recovers():
    """Within-tol mean/SD drift, integer n exact -> exact recovery (reward 1.0)."""
    human = [C("A", 4.20, 1.10, 20, 5.00, 1.30, 22)]
    pred = [C("A", 4.205, 1.10, 20, 5.00, 1.30, 22)]  # tiny mean drift, within 5%
    s = grade(pred, human)
    assert s["recovered"] == 1 and s["contradicted"] == 0, s
    assert s["reward"] == 1.0, s
    print(
        f"[PASS] D5(a) tolerant mean drift -> recovered, reward 1.0  reward={s['reward']}"
    )


def test_continuous_wrong_integer_n_contradiction():
    """A wrong integer n (counts/N never tolerant) -> contradiction."""
    human = [C("A", 4.20, 1.10, 20, 5.00, 1.30, 22)]
    pred = [C("A", 4.20, 1.10, 21, 5.00, 1.30, 22)]  # n off by one
    s = grade(pred, human)
    assert s["contradicted"] == 1 and s["recovered"] == 0, s
    assert s["reward"] == 0.0, s  # single wrong row, nothing recovered -> F = 0
    print(
        f"[PASS] D5(b) wrong integer n -> contradiction, reward 0  reward={s['reward']:.4f}"
    )


# --- population-aware denominator recovery --------------------------------


def _dich(
    study,
    outcome,
    ee,
    en,
    ce,
    cn,
    *,
    en_randomized=None,
    en_observed=None,
    en_analyzed=None,
    cn_randomized=None,
    cn_observed=None,
    cn_analyzed=None,
):
    return ArmRow(
        study_id=study,
        outcome=outcome,
        data_type="dichotomous",
        experimental_events=ee,
        experimental_n=en,
        experimental_n_randomized=en_randomized,
        experimental_n_observed=en_observed,
        experimental_n_analyzed=en_analyzed,
        control_events=ce,
        control_n=cn,
        control_n_randomized=cn_randomized,
        control_n_observed=cn_observed,
        control_n_analyzed=cn_analyzed,
    )


def test_two_denominators_one_arm_differs_recovers():
    """Gold n matches one declared population while events remain exact."""
    human = [F("Dunley 2018", "response event", 73, 240, 61, 230)]
    pred = [
        _dich(
            "Dunley 2018",
            "response event",
            73,
            235,
            61,
            230,
            en_analyzed=240,
        )
    ]
    s = grade(pred, human)
    assert s["recovered"] == 1 and s["contradicted"] == 0 and s["extras"] == 0, s
    assert s["reward"] == 1.0, s


def test_two_denominators_previously_contradiction_now_recovers():
    """With a single declared n 235 this row is a diff==1 contradiction.
    Declaring analyzed n 240 flips the
    10x-penalised contradiction into a clean recovery -- precision AND coverage
    both rise."""
    human = [F("Dunley 2018", "response event", 73, 240, 61, 230)]
    legacy = grade([_dich("Dunley 2018", "response event", 73, 235, 61, 230)], human)
    fixed = grade(
        [
            _dich(
                "Dunley 2018",
                "response event",
                73,
                235,
                61,
                230,
                en_analyzed=240,
            )
        ],
        human,
    )
    assert legacy["contradicted"] == 1 and legacy["recovered"] == 0, legacy
    assert fixed["recovered"] == 1 and fixed["contradicted"] == 0, fixed
    assert fixed["reward"] > legacy["reward"], (fixed["reward"], legacy["reward"])


def test_two_denominators_both_arms_differ_recovers():
    """Both arms recover when gold matches an explicitly declared population."""
    human = [F("Ellerton 2020", "marker event", 12, 180, 10, 176)]
    pred = [
        _dich(
            "Ellerton 2020",
            "marker event",
            12,
            173,
            10,
            169,
            en_analyzed=180,
            cn_analyzed=176,
        )
    ]
    s = grade(pred, human)
    assert s["recovered"] == 1 and s["contradicted"] == 0 and s["extras"] == 0, s
    assert s["reward"] == 1.0, s


def test_two_denominators_wrong_events_still_misses():
    """Anti-gaming lock: events stay strictly exact. A wrong event count does not
    recover even when a declared denominator matches gold."""
    human = [F("Dunley 2018", "response event", 73, 240, 61, 230)]
    pred = [
        _dich(
            "Dunley 2018",
            "response event",
            72,
            235,
            61,
            230,
            en_analyzed=240,
        )
    ]
    s = grade(pred, human)
    assert s["recovered"] == 0, s
    assert s["contradicted"] == 1, s  # only exp_events wrong -> all-but-one


def test_two_denominators_gold_matches_neither_is_not_recovered():
    """If gold's denominator equals no declared population the n is still
    wrong -> not a recovery (membership is not a free pass)."""
    human = [F("X", "outcome", 10, 500, 20, 600)]
    pred = [_dich("X", "outcome", 10, 480, 20, 600, en_analyzed=490)]
    s = grade(pred, human)
    assert s["recovered"] == 0, s
    assert s["contradicted"] == 1, s


def test_single_n_grades_exactly():
    """A row with only primary n uses strict exact matching."""
    human = [F("X", "outcome", 10, 500, 20, 600)]
    exact = grade([_dich("X", "outcome", 10, 500, 20, 600)], human)
    off = grade([_dich("X", "outcome", 10, 499, 20, 600)], human)
    assert exact["recovered"] == 1 and exact["reward"] == 1.0, exact
    assert off["recovered"] == 0 and off["contradicted"] == 1, off


@pytest.mark.parametrize(
    "field",
    ("randomized", "observed", "analyzed"),
)
def test_continuous_population_candidates_recover(field):
    """A legacy gold n may match any explicitly declared population."""
    human = [C("Li 2015", 51.32, 13.25, 96, 52.23, 12.65, 96)]
    population = {
        f"experimental_n_{field}": 96,
        f"control_n_{field}": 96,
    }
    pred = ArmRow(
        study_id="Li 2015",
        outcome="PANSS total | week 24",
        data_type="continuous",
        experimental_mean=51.32,
        experimental_sd=13.25,
        experimental_n=84,
        control_mean=52.23,
        control_sd=12.65,
        control_n=81,
        **population,
    )
    score = grade([pred], human)
    assert score["recovered"] == 1 and score["reward"] == 1.0, score


def test_population_candidates_must_match_gold_exactly():
    human = [C("Li 2015", 51.32, 13.25, 96, 52.23, 12.65, 96)]
    pred = ArmRow(
        study_id="Li 2015",
        outcome="PANSS total | week 24",
        data_type="continuous",
        experimental_mean=51.32,
        experimental_sd=13.25,
        experimental_n=84,
        experimental_n_randomized=95,
        experimental_n_observed=84,
        experimental_n_analyzed=95,
        control_mean=52.23,
        control_sd=12.65,
        control_n=81,
        control_n_randomized=95,
        control_n_observed=81,
        control_n_analyzed=95,
    )
    score = grade([pred], human)
    assert score["recovered"] == 0, score


# --- Defloor flipped-pair / pass-order guards -----------------------------


def test_defloor_flipped_pair_oracle():
    """(39,63,30,66) / (30,66,39,63) differ in all 4 fields -> never all-but-one;
    each recovers its own exact partner -> oracle 1.0."""
    human = [D("Defloor", 39, 63, 30, 66), D("Defloor", 30, 66, 39, 63)]
    s = grade(human, human)
    assert s["reward"] == 1.0 and s["recovered"] == 2 and s["contradicted"] == 0, s
    print(f"[PASS] Defloor flipped-pair oracle 1.0  recovered={s['recovered']}")


def test_pass_order_mutually_all_but_one_oracle():
    """Two same-study human rows that ARE mutually all-but-one (differ only in
    control_events). Pass 1 claims both exact partners first -> oracle 1.0.
    If Pass 2 ran first, one would force-pair as a contradiction -> reward < 1."""
    human = [D("X", 1, 100, 2, 100), D("X", 1, 100, 3, 100)]
    s = grade(human, human)
    assert s["reward"] == 1.0 and s["recovered"] == 2 and s["contradicted"] == 0, s
    print(
        f"[PASS] pass-order mutually-all-but-one oracle 1.0  recovered={s['recovered']}"
    )


def test_pass_order_genuine_near_miss_flagged():
    """On that same pair, a genuine near-miss IS still flagged as a contradiction."""
    human = [D("X", 1, 100, 2, 100), D("X", 1, 100, 3, 100)]
    pred = [D("X", 1, 100, 2, 100), D("X", 1, 100, 9, 100)]  # 2nd row one cell off
    s = grade(pred, human)
    assert s["recovered"] == 1 and s["contradicted"] == 1, s
    print(
        f"[PASS] pass-order genuine near-miss flagged  recovered={s['recovered']} contradicted={s['contradicted']}"
    )


# --- duplicate value tuples -----------------------------------------------


def test_duplicate_value_tuples_remain_distinct_rows():
    human = [D("A", 0, 386, 1, 380), D("A", 0, 386, 1, 380)]
    s = grade([], human)
    assert s["total_human"] == 2, s
    assert s["missing"] == 2, s
    print("[PASS] duplicate value-tuples remain distinct denominator rows")


def test_oracle_with_duplicates_scores_one():
    human = [D("A", 0, 386, 1, 380), D("A", 0, 386, 1, 380)]
    s = grade(human, human)
    assert s["reward"] == 1.0, s
    assert s["total_human"] == 2, s
    assert s["recovered"] == 2 and s["extras"] == 0, s
    print("[PASS] duplicate oracle scores 1.0 with duplicate pred rows")


def test_duplicate_of_one_correct_fact_is_extra_past_multiplicity() -> None:
    human = [F("A", "mortality", 8, 321, 9, 295)]
    pred = [
        P("A", "mortality", 8, 321, 9, 295),
        P("A", "mortality", 8, 321, 9, 295),
    ]

    s = grade(pred, human)

    assert s["recovered"] == 1, s
    assert s["extras"] == 1, s
    assert s["precision"] == pytest.approx(1 / 2), s
    assert s["recall"] == 1.0, s
    assert s["coverage"] == 1.0, s
    assert s["reward"] == pytest.approx(2 / 3), s


def test_emit_nothing_scores_zero_against_fact_model() -> None:
    s = grade([], [F("A", "mortality", 8, 321, 9, 295)])

    assert s["reward"] == 0.0, s
    assert s["recovered"] == 0, s
    assert s["missing"] == 1, s


def test_empty_prediction_and_reference_have_explicit_conventional_edges() -> None:
    empty_prediction = grade([], [F("A", "mortality", 8, 321, 9, 295)])
    empty_benchmark = grade([], [])
    false_positive_only = grade([P("A", "mortality", 8, 321, 9, 295)], [])

    assert empty_prediction["tp"] == 0 and empty_prediction["fp"] == 0
    assert empty_prediction["fn"] == 1 and empty_prediction["reward"] == 0.0
    assert empty_benchmark["precision"] == 1.0
    assert empty_benchmark["recall"] == 1.0
    assert empty_benchmark["reward"] == 1.0
    assert false_positive_only["precision"] == 0.0
    assert false_positive_only["recall"] == 1.0
    assert false_positive_only["reward"] == 0.0


def test_event_multiplicity_requires_token_distinct_pred_rows() -> None:
    human = [
        F(
            "A",
            "adverse events",
            0,
            60,
            1,
            60,
            kind="event",
            detail_labels=["Constipation", "Headache", "Nausea"],
            multiplicity=3,
        )
    ]
    distinct = [
        P("A", "adverse events", 0, 60, 1, 60, event="Constipation"),
        P("A", "adverse events", 0, 60, 1, 60, event="Headache"),
        P("A", "adverse events", 0, 60, 1, 60, event="Nausea"),
    ]
    identical = [
        P("A", "adverse events", 0, 60, 1, 60, event="Constipation"),
        P("A", "adverse events", 0, 60, 1, 60, event="Constipation"),
        P("A", "adverse events", 0, 60, 1, 60, event="Constipation"),
    ]

    distinct_score = grade(distinct, human)
    identical_score = grade(identical, human)

    assert distinct_score["recovered"] == 3, distinct_score
    assert distinct_score["extras"] == 0, distinct_score
    assert distinct_score["reward"] == 1.0, distinct_score
    assert identical_score["recovered"] == 1, identical_score
    assert identical_score["extras"] == 2, identical_score
    assert identical_score["missing"] == 2, identical_score
    assert identical_score["tp"] == 1
    assert identical_score["fp"] == 2
    assert identical_score["fn"] == 2
    assert identical_score["reward"] == pytest.approx(1 / 3), identical_score


def test_row_dispositions_explain_hits_non_hits_and_missing_references() -> None:
    human = [
        F("A", "mortality", 8, 321, 9, 295),
        F("A", "response", 3, 100, 4, 101),
    ]
    pred = [
        P("A", "mortality", 8, 321, 9, 295),
        P("A", "mortality", 8, 321, 9, 295),
        P("A", "response", 3, 100, 5, 101),
        P("A", "partial response", 3, None, 4, 101),
        P("B", "unmatched", 1, 10, 2, 10),
    ]

    score = grade(pred, human)
    dispositions = score["row_dispositions"]

    assert [row["disposition"] for row in dispositions] == [
        "hit",
        "duplicate",
        "contradicted",
        "partial",
        "unmatched_extra",
    ]
    assert dispositions[0]["is_hit"] is True
    assert dispositions[0]["reference_index"] == 0
    assert dispositions[1]["is_hit"] is False
    assert dispositions[1]["reference_index"] == 0
    assert dispositions[2]["reason"] == (
        "one comparable value contradicted the reference"
    )
    assert dispositions[2]["differing_fields"] == ["control_events"]
    assert dispositions[3]["reference"] is None
    assert dispositions[4]["reference"] is None
    assert score["missing_references"] == []
    missing = grade([], human)["missing_references"]
    assert [row["reference_index"] for row in missing] == [0, 1]


def test_row_dispositions_are_deterministic_under_value_ties() -> None:
    human = [
        F("A", "checkpoint one", 6, 44, 9, 46),
        F("A", "checkpoint two", 6, 44, 9, 46),
    ]
    pred = [P("A", "checkpoint two", 6, 44, 9, 46)]
    vocab = {
        "outcomes": [
            {"canonical": "checkpoint one", "synonyms": ["one"]},
            {"canonical": "checkpoint two", "synonyms": ["two"]},
        ]
    }

    first = grade(pred, human, vocab=vocab)
    second = grade(pred, human, vocab=vocab)

    assert first["row_dispositions"] == second["row_dispositions"]
    assert first["row_dispositions"][0]["reference_index"] == 1


def test_vocab_synonym_routes_to_canonical_outcome() -> None:
    human = [F("A", "iron stores | ferritin", 29, 35, 32, 35)]
    pred = [P("A", "Serum ferritin", 29, 35, 32, 35)]
    vocab = {
        "review_id": "DEMO-REVIEW",
        "outcomes": [
            {
                "canonical": "iron stores | ferritin",
                "members": [[1, 1]],
                "synonyms": ["Serum ferritin", "Ferritin (ng/mL)"],
            }
        ],
        "labels": [],
    }

    s = grade(pred, human, vocab=vocab)

    assert s["reward"] == 1.0, s
    assert s["recovered"] == 1, s


def test_reconstruct_bookkeeping_fills_recovered_fact_slots() -> None:
    human = [
        F(
            "A",
            "mortality",
            8,
            321,
            9,
            295,
            slots=[
                {"analysis_group": 1, "analysis_id": 1, "subgroup": "Female"},
                {"analysis_group": 4, "analysis_id": 1, "subgroup": "Low ferritin"},
            ],
        )
    ]
    pred = [P("A", "mortality", 8, 321, 9, 295)]

    s = grade(pred, human)

    assert s["reconstructed_rows"] == [
        {
            "analysis_group": 1,
            "analysis_id": 1,
            "subgroup": "Female",
            "study_id": "A",
            "canonical_outcome": "mortality",
            "data_type": "dichotomous",
            "experimental_events": 8,
            "experimental_n": 321,
            "control_events": 9,
            "control_n": 295,
        },
        {
            "analysis_group": 4,
            "analysis_id": 1,
            "subgroup": "Low ferritin",
            "study_id": "A",
            "canonical_outcome": "mortality",
            "data_type": "dichotomous",
            "experimental_events": 8,
            "experimental_n": 321,
            "control_events": 9,
            "control_n": 295,
        },
    ]
    assert s["reconstruction_fidelity"] == 1.0, s


# --- anti-gaming baselines (guard the smooth reward's floors) --------------


def test_degenerate_baselines_bounded():
    """Floors the redesign relies on: extract-nothing -> 0, oracle -> 1, spray -> ~0.
    These guard against a future REWARD_BETA change silently opening a gaming floor."""
    human = n_distinct_human(10)
    assert grade([], human)["reward"] == 0.0, "extract-nothing must score 0"
    assert grade(human, human)["reward"] == 1.0, "oracle must score 1"
    spray = [
        D(f"junk{i}", i + 1, 900, i + 2, 900) for i in range(40)
    ]  # 40 non-matching rows
    assert grade(spray, human)["reward"] < 0.05, "spraying rows must not buy reward"
    print("[PASS] extraction anti-gaming baselines bounded")


# --- semantic audit (policy extraction-semantic-audit-v1) ------------------
# The audit prices label meaning on top of the value-first matcher: vetoed
# hits become FP+FN, omitted timepoints earn alpha=0.5 (0 when the outcome
# has multiple gold windows). A judge stub stands in for the litellm judge;
# the exact-label short-circuit must never call it.


def _no_judge(items):
    raise AssertionError(f"judge must not be called, got {len(items)} pairs")


def _audit(pred, human, judge):
    scores = grade(pred, human)
    return G.apply_semantic_audit(scores, [G.GoldFact.model_validate(f) if not isinstance(f, G.GoldFact) else f for f in human], judge=judge)


def test_audit_exact_label_short_circuits_without_judge():
    human = [F("s1", "Deaths | 12 weeks", 8, 321, 9, 295)]
    pred = [P("s1", "Deaths | 12 weeks", 8, 321, 9, 295)]
    scores = _audit(pred, human, _no_judge)
    assert scores["reward"] == 1.0
    assert scores["semantic_audit"]["vetoed"] == 0
    assert scores["row_dispositions"][0]["semantic_verdict"] == "SAME"


def test_audit_vetoes_wrong_outcome_to_fp_plus_fn():
    """The reported hole: right numbers under the wrong meaning scored 1.0."""
    human = [
        F("s1", "Deaths | 12 weeks", 8, 321, 9, 295),
        F("s1", "Relapse | 12 weeks", 4, 321, 12, 295),
    ]
    pred = [
        P("s1", "Kidney failure at 12 weeks", 8, 321, 9, 295),
        P("s1", "Relapse | 12 weeks", 4, 321, 12, 295),
    ]

    def judge(items):
        assert len(items) == 1
        return {items[0]["pair_id"]: "OUTCOME_MISMATCH"}

    scores = _audit(pred, human, judge)
    # One of two hits vetoed: tp 2->1, fp 0->1, fn 0->1.
    assert (scores["tp"], scores["fp"], scores["fn"]) == (1, 1, 1)
    assert scores["reward"] == pytest.approx(2 * 1 / (2 * 2 + 0 + 0))
    assert scores["semantic_audit"]["vetoed"] == 1


def test_audit_timepoint_mismatch_vetoes():
    human = [F("s1", "Deaths | 12 weeks", 8, 321, 9, 295)]
    pred = [P("s1", "Deaths at 999 weeks", 8, 321, 9, 295)]
    scores = _audit(pred, human, lambda items: {items[0]["pair_id"]: "TIMEPOINT_MISMATCH"})
    assert scores["reward"] == 0.0
    assert (scores["tp"], scores["fp"], scores["fn"]) == (0, 1, 1)


def test_audit_omission_earns_half_credit_when_window_unique():
    human = [F("s1", "Deaths | 12 weeks", 8, 321, 9, 295)]
    pred = [P("s1", "Deaths", 8, 321, 9, 295)]
    scores = _audit(pred, human, lambda items: {items[0]["pair_id"]: "TIMEPOINT_OMITTED"})
    # tp stays integer-1 but the soft numerator halves: reward = 2*0.5/2.
    assert scores["reward"] == pytest.approx(0.5)
    assert (scores["tp"], scores["fp"], scores["fn"]) == (1, 0, 0)
    assert scores["semantic_audit"]["omitted_unique"] == 1


def test_audit_omission_earns_zero_when_windows_ambiguous():
    human = [
        F("s1", "Deaths | 12 weeks", 8, 321, 9, 295),
        F("s1", "Deaths | 24 weeks", 11, 321, 13, 295),
    ]
    pred = [P("s1", "Deaths", 8, 321, 9, 295)]
    scores = _audit(pred, human, lambda items: {items[0]["pair_id"]: "TIMEPOINT_OMITTED"})
    assert scores["semantic_audit"]["omitted_ambiguous"] == 1
    # Numerator drops the whole hit; denominator keeps it: 2*(1-1)/(2*1+0+1).
    assert scores["reward"] == 0.0


def test_audit_fails_closed_on_missing_verdict():
    human = [F("s1", "Deaths | 12 weeks", 8, 321, 9, 295)]
    pred = [P("s1", "Mortality at week 12", 8, 321, 9, 295)]
    with pytest.raises(SystemExit):
        _audit(pred, human, lambda items: {})


def test_audit_never_raises_reward():
    """Denominator is fixed, numerator only softens: audit <= raw for any verdict."""
    human = [F("s1", "Deaths | 12 weeks", 8, 321, 9, 295)]
    raw = grade([P("s1", "anything", 8, 321, 9, 295)], human)["reward"]
    for verdict in G.JUDGE_VERDICTS:
        scores = _audit(
            [P("s1", "anything", 8, 321, 9, 295)],
            human,
            lambda items, v=verdict: {items[0]["pair_id"]: v},
        )
        assert scores["reward"] <= raw + 1e-12
