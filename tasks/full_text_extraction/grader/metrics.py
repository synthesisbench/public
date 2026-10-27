"""Agreement statistics over yes/no answers, and the report built from them.

A judge's answer to a question is the majority of its runs (with three runs and no failures it is always defined);
pairwise and Fleiss' kappa compare those majorities. Unanimity and run-to-run stability look at every run, so a judge
that wavers shows up there even when its majority agrees."""
from __future__ import annotations

from collections import Counter
from itertools import combinations
from typing import Any

from .schema import Label, Question

LABELS: tuple[Label, ...] = ("yes", "no")
# answers[judge][run] -> {qid: label or None}
Answers = dict[str, list[dict[str, Label | None]]]


def raw_agreement(a: list[Label], b: list[Label]) -> float | None:
    return sum(x == y for x, y in zip(a, b, strict=True)) / len(a) if a else None


def cohen_kappa(a: list[Label], b: list[Label]) -> float | None:
    """Unweighted Cohen's kappa; None when chance agreement is 1 (both raters gave one and the same label throughout)."""
    if not a:
        return None
    n = len(a)
    observed = raw_agreement(a, b)
    ca, cb = Counter(a), Counter(b)
    chance = sum(ca[label] * cb[label] for label in LABELS) / (n * n)
    return None if chance == 1 else (observed - chance) / (1 - chance)


def fleiss_kappa(rows: list[list[Label]]) -> float | None:
    """Fleiss' kappa over items each rated by the same number of raters; None when chance agreement is 1."""
    if not rows:
        return None
    raters = len(rows[0])
    if raters < 2 or any(len(row) != raters for row in rows):
        raise ValueError("every item needs the same number (>= 2) of ratings")
    counts = [Counter(row) for row in rows]
    observed = sum((sum(c[label] ** 2 for label in LABELS) - raters) / (raters * (raters - 1)) for c in counts) / len(rows)
    shares = [sum(c[label] for c in counts) / (len(rows) * raters) for label in LABELS]
    chance = sum(share ** 2 for share in shares)
    return None if chance == 1 else (observed - chance) / (1 - chance)


def majority(labels: list[Label | None]) -> Label | None:
    """The label most runs gave; None when no run answered or the answered runs tie."""
    ranked = Counter(label for label in labels if label).most_common()
    if not ranked or (len(ranked) > 1 and ranked[0][1] == ranked[1][1]):
        return None
    return ranked[0][0]


def unanimous(labels: list[Label | None]) -> bool:
    return all(labels) and len(set(labels)) == 1


def rate(hits: int, n: int) -> dict[str, Any]:
    return {"count": hits, "of": n, "rate": hits / n if n else None}


def group_summary(questions: list[Question], answers: Answers) -> dict[str, Any]:
    judges = list(answers)
    runs = {judge: [[run.get(q.qid) for run in answers[judge]] for q in questions] for judge in judges}
    votes = {judge: [majority(labels) for labels in runs[judge]] for judge in judges}

    pairwise = {}
    for a, b in combinations(judges, 2):
        both = [(x, y) for x, y in zip(votes[a], votes[b]) if x and y]
        xs, ys = [x for x, _ in both], [y for _, y in both]
        pairwise[f"{a}~{b}"] = {"n": len(both), "agreement": raw_agreement(xs, ys), "kappa": cohen_kappa(xs, ys)}

    complete = [list(row) for row in zip(*(votes[j] for j in judges)) if all(row)]
    every_run = [sum((runs[j][i] for j in judges), []) for i in range(len(questions))]
    answered = [labels for labels in every_run if all(labels)]

    stability, errors = {}, {}
    for judge in judges:
        full = [labels for labels in runs[judge] if all(labels)]
        stability[judge] = rate(sum(len(set(labels)) == 1 for labels in full), len(full))
        errors[judge] = {"majority": label_errors(questions, votes[judge]),
                         "runs": [label_errors(questions, [run.get(q.qid) for q in questions]) for run in answers[judge]]}

    split = [{"qid": q.qid, "set": q.set, "expected": q.expected, "meta": q.meta,
              "answers": {j: runs[j][i] for j in judges}}
             for i, q in enumerate(questions) if not unanimous(every_run[i])]
    return {
        "n": len(questions),
        "pairwise": pairwise,
        "fleiss": {"n": len(complete), "kappa": fleiss_kappa(complete) if len(judges) > 1 else None},
        "unanimity": rate(sum(len(set(labels)) == 1 for labels in answered), len(answered)),
        "stability": stability,
        "errors": errors,
        "split": split,
    }


def label_errors(questions: list[Question], given: list[Label | None]) -> dict[str, Any]:
    """Against the intended label: false-equivalent = said yes to an intended no; false-not-equivalent = said no to an
    intended yes. Denominators count only answered questions with that intended label."""
    positives = [label for q, label in zip(questions, given) if q.expected == "yes" and label]
    negatives = [label for q, label in zip(questions, given) if q.expected == "no" and label]
    return {"false_equivalent": rate(negatives.count("yes"), len(negatives)),
            "false_not_equivalent": rate(positives.count("no"), len(positives))}


def summarize(questions: list[Question], answers: Answers) -> dict[str, Any]:
    """Per question set and overall ("all")."""
    sets = sorted({q.set for q in questions})
    groups = {name: [q for q in questions if q.set == name] for name in sets}
    if len(sets) > 1:
        groups["all"] = questions
    return {name: group_summary(subset, answers) for name, subset in groups.items()}
