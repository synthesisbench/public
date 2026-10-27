# MetaPsy Risk of Bias Handbook

- **Primary source:** https://www.metapsy.org/rob/handbook/
- **PDF source:** https://www.metapsy.org/assets/rob/guidance.pdf
- **Handbook version displayed by the site:** 1.0-0
- **Retrieved:** 2026-07-19

This is a concise, locally navigable summary of the MetaPsy Risk of Bias (RoB) handbook for psychotherapy trials. It restates the operational guidance in original language; it is not a verbatim copy and does not contain judgments for any MetaPsy study or benchmark instance.

## Scope and assessment target

The source describes 24 signalling items across five domains. Every item points in the same direction: `Yes` or `PY` (probably yes) generally supports lower risk; `No` or `PN` (probably no) generally supports higher risk; `NI` means no information. The [algorithms](algorithms.md) collapse `PY` into `Yes` and `PN` into `No`.

The guidance is designed for individually randomized, parallel-group psychotherapy trials. Parts may transfer to cluster-randomized or crossover designs, but the handbook warns that those designs need additional treatment, referring reviewers to Cochrane RoB 2. Ratings should target a particular numeric result for a particular outcome at a particular time point, even though some biases operate study-wide. The intended estimand is the effect of assignment to intervention, not the effect of adhering to intervention.

## Handbook navigation

1. [Domain 1: Randomization process](domain-1-randomization.md) — items 1–4
2. [Domain 2: Deviations from intended interventions](domain-2-deviations.md) — items 5–9
3. [Domain 3: Missing outcome data](domain-3-missing-data.md) — items 10–14
4. [Domain 4: Measurement of the outcome](domain-4-outcome-measurement.md) — items 15–18
5. [Domain 5: Selective outcome reporting](domain-5-selective-reporting.md) — items 19–24
6. [Domain and overall algorithms](algorithms.md)

## Source-stated workflow and tooling

The linked PDF supplies workflow details not all repeated on the HTML welcome page:

- The interactive RoB Assistant asks only questions needed by the current decision path, calculates domain and overall judgments, and exports results: https://www.metapsy.org/rob/assistant/
- Experienced raters can instead use the RoB extraction-sheet template. With a conforming MetaPsy database, `createRobRatings` can populate tagged items and calculate ratings: https://tools.metapsy.org/reference/createrobratings
- The PDF names the relevant database inputs as baseline arm means, standard deviations and sample sizes; randomization ratio and randomized arm counts; arm-level attrition; and rating type. The function documentation also specifies the signalling-item columns (`d1_1` through `d5_24`, plus notes).
- The PDF recommends two independent reviewers, consensus discussion for discrepancies, and senior adjudication when needed. `checkRobDiscrepancies` can flag disagreements and report Cohen's kappa.

Items tagged for possible automatic completion in the handbook are 3, 4, 10, 12, 13, 16, and 17. Automation does not remove the handbook's explicit allowance for reviewer judgment where the algorithm does not capture a clinically important prognostic imbalance.

## How to use this local summary

The domain files separate **source-stated rules** from short **working syntheses**. A working synthesis only orders or condenses the stated rules; it is not an additional decision rule. Apply the result-, outcome-, and time-point scope before answering any item, then use the algorithm page after completing the applicable items.

## License check

No license or copyright notice was displayed on any of the seven handbook HTML pages, and no license statement was found in the linked handbook PDF on 2026-07-19. A related MetaPsy RoB preprint is marked CC BY-NC 4.0, but that notice is not treated here as a license for the handbook pages or PDF: https://www.medrxiv.org/content/10.1101/2025.06.26.25330349v1.full.pdf

Accordingly, these files provide compact original-language summaries and retain only operationally necessary item names, thresholds, examples, and decision logic.

## Coverage record

All pages in the handbook's table of contents were visited:

- https://www.metapsy.org/rob/handbook/
- https://www.metapsy.org/rob/handbook/domain-1
- https://www.metapsy.org/rob/handbook/domain-2
- https://www.metapsy.org/rob/handbook/domain-3
- https://www.metapsy.org/rob/handbook/domain-4
- https://www.metapsy.org/rob/handbook/domain-5
- https://www.metapsy.org/rob/handbook/rating

Linked supporting materials checked were the handbook PDF, RoB Assistant, `createRobRatings` documentation, and the related preprint listed above.

## Known source ambiguities

- Domain 5 is labeled both “Selective outcome reporting” and “Selection of the reported result” across current source surfaces; this summary uses the HTML page title while preserving the same six items.
- For item 10, the HTML says that continuous endpoint availability above 95% permits a low-risk judgment, while the PDF explicitly says this threshold applies in both groups. The domain summary records both formulations.
- Item 21 describes prospective specification as occurring before data collection, then parenthetically refers to a one-month window around enrollment start. The summary preserves both ideas rather than resolving the timing ambiguity.
- The algorithms page lists decision rows rather than a complete formal specification. Some response combinations are not explicitly covered, especially in domain 4. This summary does not fill those gaps by inference.
- The related medRxiv preprint's license statement was visible in indexed PDF text, but a direct automated fetch of its PDF returned HTTP 403 during verification. This did not affect access to any handbook page or the handbook PDF.
