# Task Contracts

Each stage is a Harbor task under `tasks/<task>/`: the agent instruction in
`steps/<step>/instruction.md`, the grader in `tests/grade.py`, and a floor
regression suite beside it. A private builder pairs the contract with one
review's staged files (mounted as `/task`) and a verifier-only reference
(`/tests/human` or `/tests/gold`), so no instance or answer key lives here.
Every grader rejects malformed key sets, invented IDs, missing outputs, and
non-finite values, and returns a deterministic reward in `[0, 1]`.

## title_abstract_screening

- **Inputs:** `screen_in.json` (a frozen sample of the review's search pool),
  one abstract per candidate under `papers/`, and `criteria.md`.
- **Output:** `decisions.json`, an `include` or `exclude` decision per
  candidate.
- **Verifier:** chance-corrected agreement with the review's known-positive
  set, weighted so a missed positive costs ten times an extra include; neither
  including nor excluding everything scores well.

## full_text_screening

- **Inputs:** `screen_in.json`, each candidate's full text under `papers/`, and
  `criteria.md`.
- **Output:** `decisions.json`, an `include` or `exclude` decision per
  study.
- **Verifier:** the same 10:1 asymmetric chance-corrected agreement, against
  the review's include/exclude decision for every study whose full text was
  staged.

## full_text_extraction

- **Inputs:** the included studies' full texts under `papers/` and a
  result-free `review_context.md`; the agent infers which outcomes are in scope.
- **Output:** `extractions.json`, per-arm numeric rows plus study
  characteristics, with `*_n` as the arm denominator.
- **Verifier:** F1 over deterministic row matching. A value that contradicts
  the paper counts as both a false positive and a false negative, so
  fabrication scores worse than honest omission.

## risk_of_bias

- **Inputs:** `rob_in.json` (study, outcome, and domains to judge), the full
  texts, `review_context.md`, and the RoB guidance under `resources/rob/`.
- **Output:** `judgements.json`, nested as study → outcome → domain → a low,
  unclear, or high judgment. The outcome key is the task's `outcome` verbatim,
  or `"study-level"` when it is null.
- **Verifier:** linear-weighted Cohen's kappa against the expert judgments on
  the component domains, so any single-label shortcut scores zero and a near
  miss costs less than a polar inversion. Overall bias is diagnostic only.

## meta_analysis

- **Inputs:** `meta_in.json` (raw per-study arm rows per analysis, no
  precomputed effects or weights) and `meta_methods.md` (effect measure, model,
  heterogeneity estimator, CI method).
- **Output:** `analyses.json`, a pooled estimate, 95% CI, and I² per analysis.
- **Verifier:** the point estimate and both CI bounds must match within the
  declared tolerance; omitted analyses score zero, and conclusions are
  diagnostic only.

`tasks/smoke/` is a Harbor wiring check, not a benchmark stage. Run every
suite with `uv run --frozen python -m pytest -q` and prove the floor tests are
load-bearing with `bash scripts/sabotage.sh`.
