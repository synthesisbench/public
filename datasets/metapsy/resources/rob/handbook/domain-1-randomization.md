# Domain 1: Randomization Process

- **Source:** https://www.metapsy.org/rob/handbook/domain-1
- **Supplementary source:** https://www.metapsy.org/assets/rob/guidance.pdf
- **Retrieved:** 2026-07-19

[Handbook index](README.md) · [Decision algorithm](algorithms.md#domain-1)

## Source-stated rules

### Item 1 — Random allocation sequence

Answer `Yes/PY` when sequence generation included chance. Examples include computer-generated random numbers, random-number tables, dice, and coin tosses.

### Item 2 — Concealment during enrollment and assignment

Answer `Yes/PY` when enrolling personnel could not predict or influence the next assignment. Qualifying approaches include remote or central allocation administered independently of enrollment staff and sealed envelopes; the PDF specifies properly sealed, opaque envelopes.

### Item 3 — Balance in randomized group sizes

This item is tagged for `createRobRatings`. Compare the observed proportion assigned to an arm with the planned randomization proportion using a 99% confidence interval. If the interval excludes the expected allocation (for example, 0.50 under a 1:1 ratio), the handbook treats that as suspicion of imbalance. The RoB Assistant can perform the calculation.

### Item 4 — Balance in baseline clinical severity

This item is also tagged for `createRobRatings`. Calculate the baseline standardized mean difference (SMD) and its 99% confidence interval. The stated imbalance signal is both:

- SMD greater than 0.2; and
- the 99% confidence interval's lower limit greater than 0.

For multiple clinical-severity tests, p-values or confidence intervals may be Bonferroni-adjusted. Baseline severity is the standard focus because it is widely reported, objectively comparable, and prognostic. Reviewers may add disorder-specific prognostic factors and override the proposed algorithm when clinical judgment identifies an important imbalance not captured by these items.

## Working synthesis

First establish whether allocation was truly random and concealed. Then test whether the observed arm counts and baseline severity are compatible with the planned randomization. Do not equate a balanced-looking baseline with adequate concealment: the [domain algorithm](algorithms.md#domain-1) gives item 2 a decisive role.

[Next: Domain 2](domain-2-deviations.md)

