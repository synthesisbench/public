import pytest

from grader import metrics
from grader.schema import Question


def test_cohen_kappa_on_a_known_table():
    # 50 ratings: 20 yes/yes, 5 yes/no, 10 no/yes, 15 no/no -> observed 0.7, chance 0.5*0.6 + 0.5*0.4 = 0.5, kappa 0.4.
    a = ["yes"] * 25 + ["no"] * 25
    b = ["yes"] * 20 + ["no"] * 5 + ["yes"] * 10 + ["no"] * 15
    assert metrics.raw_agreement(a, b) == pytest.approx(0.7)
    assert metrics.cohen_kappa(a, b) == pytest.approx(0.4)


def test_cohen_kappa_is_undefined_when_both_raters_never_vary():
    assert metrics.cohen_kappa(["yes"] * 3, ["yes"] * 3) is None
    assert metrics.cohen_kappa([], []) is None


def test_fleiss_kappa_on_a_known_table():
    # Per-item agreement 1, 1, 1/3, 1/3 -> mean 2/3; yes share 6/12 -> chance 1/2; kappa (2/3 - 1/2) / (1/2) = 1/3.
    rows = [["yes", "yes", "yes"], ["no", "no", "no"], ["yes", "yes", "no"], ["yes", "no", "no"]]
    assert metrics.fleiss_kappa(rows) == pytest.approx(1 / 3)
    assert metrics.fleiss_kappa([["yes", "yes"], ["yes", "yes"]]) is None
    with pytest.raises(ValueError):
        metrics.fleiss_kappa([["yes", "yes"], ["yes"]])


def question(qid, expected):
    # A fictional study: no real trial, drug or author.
    fact = {"study_id": "Fixture 2099", "outcome": "Walking distance", "experimental_arm": "Exercise programme", "control_arm": "Waiting list"}
    return Question(qid=qid, set="fixture", context="Adults with a fictional condition.", prediction=fact, reference=fact, expected=expected)


def test_summary_counts_unanimity_stability_errors_and_splits():
    questions = [question("q1", "yes"), question("q2", "no"), question("q3", "yes")]
    answers = {
        "a": [{"q1": "yes", "q2": "no", "q3": "yes"}] * 3,
        "b": [{"q1": "yes", "q2": "no", "q3": "no"}] * 3,
        # c says yes to q2 twice, then no: majority yes, unstable.
        "c": [{"q1": "yes", "q2": "yes", "q3": "yes"}, {"q1": "yes", "q2": "yes", "q3": "yes"}, {"q1": "yes", "q2": "no", "q3": "yes"}],
    }
    group = metrics.summarize(questions, answers)["fixture"]

    assert group["n"] == 3
    assert group["unanimity"] == {"count": 1, "of": 3, "rate": pytest.approx(1 / 3)}
    assert {j: (s["count"], s["of"]) for j, s in group["stability"].items()} == {"a": (3, 3), "b": (3, 3), "c": (2, 3)}
    # majorities a [y n y], b [y n n]: agreement 2/3, chance (2*1 + 1*2)/9 = 4/9, kappa (2/3 - 4/9)/(5/9) = 0.4
    assert group["pairwise"]["a~b"] == {"n": 3, "agreement": pytest.approx(2 / 3), "kappa": pytest.approx(0.4)}
    # a [y n y], c [y y y]: chance (2*3)/9 = 2/3 equals observed, kappa 0
    assert group["pairwise"]["a~c"]["kappa"] == pytest.approx(0.0)
    # rows [y y y], [n n y], [y n y]: mean agreement 5/9, chance (6/9)^2 + (3/9)^2 = 5/9, kappa 0
    assert group["fleiss"] == {"n": 3, "kappa": pytest.approx(0.0)}
    assert group["errors"]["b"]["majority"]["false_not_equivalent"] == {"count": 1, "of": 2, "rate": 0.5}
    assert group["errors"]["c"]["majority"]["false_equivalent"] == {"count": 1, "of": 1, "rate": 1.0}
    assert [run["false_equivalent"]["count"] for run in group["errors"]["c"]["runs"]] == [1, 1, 0]
    assert [s["qid"] for s in group["split"]] == ["q2", "q3"]
    assert group["split"][0]["answers"]["c"] == ["yes", "yes", "no"]


def test_missing_answers_shrink_denominators_and_count_as_split():
    questions = [question("q1", "yes"), question("q2", "no")]
    answers = {"a": [{"q1": "yes", "q2": None}], "b": [{"q1": "yes", "q2": "no"}]}
    group = metrics.summarize(questions, answers)["fixture"]
    assert group["unanimity"]["of"] == 1 and group["pairwise"]["a~b"]["n"] == 1
    assert group["errors"]["a"]["majority"]["false_equivalent"]["of"] == 0
    assert [s["qid"] for s in group["split"]] == ["q2"]


def test_summary_adds_an_overall_group_across_sets():
    questions = [question("q1", "yes"), question("q2", "no").model_copy(update={"set": "other"})]
    answers = {"a": [{"q1": "yes", "q2": "no"}], "b": [{"q1": "yes", "q2": "no"}]}
    summary = metrics.summarize(questions, answers)
    assert list(summary) == ["fixture", "other", "all"] and summary["all"]["n"] == 2
