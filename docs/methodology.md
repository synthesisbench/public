# Methodology

The benchmark makes five measurement claims. Each claim has an observable check.

## 1. Degenerate strategies do not earn strong rewards

Screening chance-corrects a 10:1 false-negative:false-positive cost; extraction requires actual fact recovery;
risk-of-bias agreement is corrected for chance; meta-analysis requires the
numbers.

The regression suites pin the important floors:

| Strategy | Expected behavior | Check |
| --- | --- | --- |
| include or exclude everything | zero screening reward | `tasks/title_abstract_screening/tests/test_grade.py`, `tasks/full_text_screening/tests/test_grade.py` |
| extract nothing | zero extraction reward | `tasks/full_text_extraction/tests/test_extraction_grade.py` |
| assign the majority bias label | zero chance-corrected reward | `tasks/risk_of_bias/tests/test_grade.py` |
| submit a conclusion with wrong estimates | zero numeric agreement | `tasks/meta_analysis/tests/test_grade.py` |

## 2. The floor tests discriminate

A green suite alone can be decorative. `scripts/sabotage.sh` deliberately
weakens each grader and requires its named floor test to fail. A mutation that
survives is a measurement failure even if the unmodified suite is green.

## 3. A perfect staged answer scores 1.0

Before a model run, the private builder replays each instance's verifier-only
reference through the exact staged grader. It checks that the staged grader is
byte-identical to the public one, constructs the perfect payload, and requires a
reward of 1.0, binding the result to hashes of the instance, grader, reference,
payload, and result.

A failing oracle indicates broken staging or grading. The benchmark must not
reinterpret it as model difficulty.

## 4. The agent cannot see the answer

Agent-visible work is staged under `/task`. References live under `/tests/human`
or `/tests/gold` in a separately built verifier image. The task instructions do
not reveal reward formulas. Private builders enforce this split when they create
instances; the public task contracts preserve it at runtime.

## 5. Memory is not accepted as document work

The live benchmark favors recently published source material. Targets that could
plausibly be recovered from a review title or remembered conclusion are excluded.
For meta-analysis, for example, the graded target is the pooled point estimate and
confidence interval, not the prose conclusion.

Benchmark corpora and instances, including MetaPsy, stay private. See
[Provenance](provenance.md).

## Limits

This repository publishes contracts and verifiers, not model performance. It
contains no instances, answer keys, benchmark scores, copyrighted source papers,
review corpora, or licensed reference material. Passing these
checks proves the measurement code is self-consistent; it does not establish
that any model performs well on evidence synthesis.
