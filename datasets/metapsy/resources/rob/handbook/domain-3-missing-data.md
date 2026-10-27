# Domain 3: Missing Outcome Data

- **Source:** https://www.metapsy.org/rob/handbook/domain-3
- **Supplementary source:** https://www.metapsy.org/assets/rob/guidance.pdf
- **Retrieved:** 2026-07-19

[Handbook index](README.md) · [Previous domain](domain-2-deviations.md) · [Decision algorithm](algorithms.md#domain-3)

## Source-stated rules

### Item 10 — Outcome availability for nearly all randomized participants

This item is tagged for `createRobRatings`.

For continuous outcomes, availability above 95% permits the domain to be rated low risk without later questions. Availability means actual endpoint observations, not values filled by last observation carried forward (LOCF) or another imputation. The HTML refers to the proportion with endpoint data generally; the linked PDF says the threshold must be met in both groups.

For dichotomous outcomes, evaluate missingness relative to event frequency rather than applying the continuous-outcome threshold mechanically. Bias is less plausible when observed events greatly outnumber participants with missing outcomes.

### Item 11 — Appropriate handling of missingness

If item 10 is `No/PN` or `NI`, the handbook accepts these approaches:

- mixed models for repeated measures (MMRM), including mixed/growth-curve models, using at least two post-baseline measurements;
- multiple imputation that accounts for imputation uncertainty (for example with Rubin's rules), includes important auxiliary variables such as intermediate outcomes, imputes separately by randomized group, and uses a controlled or reference-based method such as jump-to-reference with suitable external information;
- sensitivity analyses spanning plausible missingness mechanisms and supporting the primary result.

LOCF is explicitly not appropriate. If no appropriate analysis is available, or reporting is unclear, continue to items 12–14.

### Item 12 — Trial size

Tagged for `createRobRatings`. Answer `Yes/PY` when at least 40 participants per arm supplied reported outcome data.

### Item 13 — Minimum completion in every arm

Tagged for `createRobRatings`. Answer `Yes/PY` when at least 70% of randomized participants in each arm completed the post-treatment assessment.

### Item 14 — Indirect evidence that missingness is unrelated to outcome

Review three possible warning signs:

1. Reported reasons imply that missingness may depend on the unobserved outcome value. A reason external to outcome, such as funding termination, is not such a warning.
2. Dropout proportions are substantially imbalanced between groups. The source's rule of thumb says the between-group difference should remain below 20 percentage points.
3. Reasons for missingness differ by group in a way related to severity or outcome.

If any warning is present, answer `No/PN`. Answer `Yes/PY` only when reporting is sufficient to assess all three and none is present. Use `NI` when the evidence is insufficient.

## Working synthesis

Use observed endpoint availability first, then a defensible missing-data analysis. Only when neither establishes low risk should size, per-arm completion, and evidence about the missingness mechanism determine the algorithmic path. The [algorithm](algorithms.md#domain-3) deliberately combines those three fallback signals rather than treating any one as conclusive.

[Next: Domain 4](domain-4-outcome-measurement.md)

