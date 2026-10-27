# Meta-analysis

You are doing a local meta-analysis stage for this review dataset. Use only the
files staged under `/task`; do not use the web or any external sources. Pool each
analysis's per-study arm rows into one overall estimate.

The analyses are in `/task/meta_in.json`: the `review_id` and an `analyses` array.
The review's result-free method choices are in `/task/meta_methods.md`; follow
those settings when selecting effect measure, model, scale, confidence level,
heterogeneity estimator, CI method, and continuity or swap handling. For a
random-effects model, use the named `heterogeneity_estimator` (e.g. REML for
inverse-variance, DL for Mantel-Haenszel) and build the interval with the named
`ci_method` (e.g. Wald). These set the interval width: the same point estimate
under a different variance convention yields a different interval, so use the
conventions named in `/task/meta_methods.md`.

## Statistical conventions

Don't substitute a generic inverse-variance random-effects pooler for a
`statistical_method = MH` row — the Mantel-Haenszel label changes the
heterogeneity calculation, not just the point estimate. For a dichotomous
Risk Ratio row with experimental events/total `a_i`/`n1_i` and control
events/total `c_i`/`n2_i` per study *i* (`N_i = n1_i + n2_i`):

- The Mantel-Haenszel fixed-effect summary is
  `theta_MH = ln( sum(a_i * n2_i / N_i) / sum(c_i * n1_i / N_i) )`.
- For `heterogeneity_estimator = DL`, compute each study's own log risk
  ratio `theta_i` and inverse-variance weight `w_i = 1 / v_i` from its own
  2x2 table, then center the heterogeneity statistic on the **MH summary**,
  not on a naive inverse-variance fixed-effect summary:
  `Q = sum( w_i * (theta_i - theta_MH)^2 )`. Derive
  `tau^2 = max(0, (Q - (k-1)) / (sum(w_i) - sum(w_i^2)/sum(w_i)))` and
  report `i_squared = max(0, (Q - (k-1)) / Q) * 100`.
- Build the random-effects point estimate and Wald CI the standard generic
  inverse-variance way, using `w_i* = 1 / (v_i + tau^2)` — the MH label only
  changes what `theta_MH` centers `Q` on, not how the final random-effects
  weights are formed. The same MH-centering principle applies to Odds Ratio
  and Peto Odds Ratio rows, using that effect measure's own Mantel-Haenszel
  construction.

For `heterogeneity_estimator = REML` rows, `tau^2` is the actual restricted
maximum-likelihood estimate (an iterative fit), not the closed-form DL
estimator. The two are not interchangeable: they yield different CI widths and
different `i_squared`. Report `i_squared` for REML rows as
`tau^2 / (tau^2 + s2_typical) * 100`, where
`s2_typical = (k-1) * sum(w_i) / (sum(w_i)^2 - sum(w_i^2))` using the fixed
inverse-variance weights `w_i = 1 / v_i`.

Reference methodology material may be staged under `/task/resources/`. If
present, use it as general guidance on the synthesis and pooling conventions
above. It is a general reference and contains nothing specific to this review.
Whether or not it is staged, every review-specific method choice you need —
effect measure, model, scale, confidence level, heterogeneity estimator, CI
method, and continuity or swap handling — is in `/task/meta_methods.md`.

Each analysis has:

- `analysis_group` and `analysis_id` — the analysis numbers. **Copy both
  back unchanged**; together they identify which analysis an estimate belongs to.
- `analysis_name` — a label, for your reference only.
- `data_type` — `"dichotomous"` or `"continuous"`.
- `arms` — one row per study, each with an `experimental` and a `control` arm:
  - dichotomous: `{"events": int, "total": int}`
  - continuous: `{"mean": float, "sd": float, "total": int}`

There are no pre-computed per-study effects or weights — compute from the raw
counts and means while following `/task/meta_methods.md`.

## Your job, per analysis

1. Use the staged method context to choose the effect measure and report it
   verbatim in `effect_measure`. Use one of these recognized names:
   `Risk Ratio`, `Odds Ratio`, `Peto Odds Ratio`, `Hazard Ratio`,
   `Rate Ratio`, `Ratio of Geometric Means` (ratio measures, no-effect = 1);
   `Mean Difference`, `Std. Mean Difference`, `Risk Difference` (difference
   measures, no-effect = 0).
2. Use the staged method context to choose the model — `Fixed effect` or
   `Random effect` — and report it in `analysis_model`.
3. **Pool** the arms into one overall estimate: a point estimate and a 95%
   confidence interval, on the **natural scale** (e.g. a Risk Ratio of `0.80`, not
   its log). Ratio measures must be positive.
4. Report between-study heterogeneity as `i_squared` (0–100). I² is mathematically
   undefined for a single-study analysis. Report `0.0` in that case, not `null`.

Some dichotomous analyses contain zero-cell rows. For a study with exactly one
zero cell in its 2x2 table, add 0.5 to all four cells before computing that
study's own log-effect and variance. For a ratio measure (Risk Ratio, Odds Ratio,
and so on), a study with 0 events in both arms has an undefined ratio and infinite
variance: drop it from that analysis entirely rather than continuity-correcting it in.

## Output

Write `/task/analyses.json` as **raw JSON only** — no markdown fences, no commentary:

```json
{
  "analyses": [
    {
      "analysis_group": 9,
      "analysis_id": 9,
      "effect_measure": "Odds Ratio",
      "analysis_model": "Random effect",
      "pooled": {"mean": 0.62, "ci_start": 0.41, "ci_end": 0.94},
      "i_squared": 37.0
    }
  ]
}
```

The values above are an illustrative shape only — they do not correspond to any
analysis in your input. Compute your own from the arm data.

- One entry per analysis — cover **every** analysis in the input.
- Copy `analysis_group` and `analysis_id` exactly.
- `pooled` carries `mean`, `ci_start`, `ci_end` on the natural scale.
