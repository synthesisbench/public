# Grader statistics reference

This document specifies the calculations needed to author synthetic `meta_human`
records. It describes methodology, not any benchmark instance or reference result.

## What the verifier compares

For each gold record, the verifier finds a submitted record by the exact integer
pair `(analysis_group, analysis_id)`. The pair is the complete key; the same
`analysis_id` in two groups denotes two distinct analyses. Submitted records are
placed in a dictionary by this pair, so a later duplicate submitted key replaces an
earlier one. Missing gold keys contribute zero when metrics are averaged over the
full number of gold records. See `grade.py` lines 224-246.

The numeric comparison uses `pooled.mean`, `pooled.ci_start`, and
`pooled.ci_end`. The two interval endpoints are compared in their given positions;
they are not rounded or reordered for this check. `i_squared` is compared
separately as a diagnostic. See `grade.py` lines 126-145 and 168-175.

There is no decimal-place rule:

- For a ratio measure, every submitted value must be positive. A value passes when
  `abs(log(submitted) - log(gold)) <= 0.05`; this is an absolute tolerance on the
  log scale, equivalent to a multiplicative factor of `exp(0.05)`.
- For a difference measure, a value passes when
  `abs(submitted - gold) <= max(0.05 * max(abs(gold), 1), 1e-6)`.
- Both CI endpoints must pass their respective point comparison. I-squared passes
  within 5 absolute percentage points; two missing values also match.

These constants and comparisons are defined in `grade.py` lines 58-69 and 92-118.
The gold record's effect measure determines whether the three pooled numbers use
the ratio or difference tolerance (`grade.py` lines 164-174).

`effect_measure` and `analysis_model` are matched by stripping surrounding
whitespace, lowercasing, and then requiring exact string equality. These label
matches are diagnostics rather than part of the pooled-number comparison. There is
no scale string to match. `log_scale_data` is a boolean fallback used only when an
effect-measure name is not recognized; recognized ratio and difference names
determine scale semantically. The submitted scale is used for submitted
direction/significance diagnostics, while the gold scale controls numeric
tolerance. See `grade.py` lines 31-50, 135-145, and 157-187.

## Statistics used to author gold

The verifier does not read study arms and does not recompute an effect, variance,
heterogeneity statistic, or confidence interval. It validates already-pooled
numbers from the submitted and gold records (`grade.py` lines 126-145 and
157-207). Gold is loaded from the first sorted `/tests/gold/*.json` file and its
`meta_human` array (`grade.py` lines 253-277). Consequently, the formulas below are
the methodology the dataset author must apply before writing gold; they are not a
second implementation hidden in the verifier.

Let study `i` have experimental events/non-events `a_i`, `b_i`, control
events/non-events `c_i`, `d_i`, arm totals `n1_i = a_i + b_i` and
`n0_i = c_i + d_i`, and `N_i = n1_i + n0_i`.

### Fixed-effect Mantel-Haenszel risk ratio

Define

```text
R = sum_i(a_i * n0_i / N_i)
S = sum_i(c_i * n1_i / N_i)
theta_MH = log(R / S)
RR_MH = exp(theta_MH)
```

For its conventional fixed-effect Wald interval, use

```text
var(theta_MH) =
  sum_i((n1_i*n0_i*(a_i+c_i) - a_i*c_i*N_i) / N_i^2) / (R*S)
SE = sqrt(var(theta_MH))
CI = exp(theta_MH +/- z_(1-alpha/2) * SE)
```

At 95% confidence, `z_(1-alpha/2) = 1.959963984540054`.

### Inverse-variance mean difference

For experimental and control means `m1_i`, `m0_i`, standard deviations `s1_i`,
`s0_i`, and sample sizes `n1_i`, `n0_i`, define

```text
y_i = m1_i - m0_i
v_i = s1_i^2 / n1_i + s0_i^2 / n0_i
w_i = 1 / v_i
mu_fixed = sum_i(w_i*y_i) / sum_i(w_i)
SE_fixed = sqrt(1 / sum_i(w_i))
CI_fixed = mu_fixed +/- z_(1-alpha/2) * SE_fixed
```

Mean differences remain on the linear scale; do not exponentiate them.

### DerSimonian-Laird random effects

For each study effect `y_i` on its analysis scale and sampling variance `v_i`, set
`w_i = 1/v_i`, `df = k-1`, and

```text
C = sum_i(w_i) - sum_i(w_i^2) / sum_i(w_i)
Q = sum_i(w_i * (y_i - theta_center)^2)
tau^2_DL = max(0, (Q - df) / C)
w_i_star = 1 / (v_i + tau^2_DL)
mu_random = sum_i(w_i_star*y_i) / sum_i(w_i_star)
SE_random = sqrt(1 / sum_i(w_i_star))
CI_random = mu_random +/- z_(1-alpha/2) * SE_random
I^2 = max(0, (Q - df) / Q) * 100
```

Use `I^2 = 0` when `Q = 0` or only one study remains. For ordinary
inverse-variance analyses, `theta_center = sum(w_i*y_i)/sum(w_i)`. For an
MH-labelled risk-ratio analysis, use each study's
`y_i = log((a_i/n1_i)/(c_i/n0_i))` and
`v_i = 1/a_i - 1/n1_i + 1/c_i - 1/n0_i`, but center `Q` on `theta_MH` above.
The final random-effects point and interval still use `w_i_star`. Exponentiate
`mu_random` and both interval endpoints for a ratio measure; retain the linear
values for a difference measure.

### Zero events and continuity correction

For a dichotomous study with exactly one zero cell in its 2-by-2 table, add `0.5`
to all four cells before calculating that study's log effect and variance. Drop a
study with zero events in both arms because it contains no relative-effect
information. The verifier does not inspect these choices itself; they matter only
through the gold pooled numbers it compares (`grade.py` lines 157-175).
