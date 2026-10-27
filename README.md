# synthesis-bench-public

**Can an AI agent do real medical deep research?** synthesis-bench measures the
long-horizon, multi-document work behind medical evidence synthesis — deep
research over scientific articles, with statistical analysis on the extracted
data.

Evidence synthesis is how medicine answers "does this treatment work?" at the
standard a clinical guideline requires. A trained team spends months on a
four-stage pipeline:

1. **Search** — query bibliographic databases for every potentially relevant
   study.
2. **Filter** — screen thousands of candidates by title and abstract, then
   read each surviving paper in full against precise eligibility criteria.
3. **Extract** — pull the numeric results and study details out of every
   included paper.
4. **Analyze** — judge each study's risk of bias and pool the extracted data
   into one statistical estimate: the meta-analysis.

The published review documents every decision the team made, so each stage
downstream of Search can be re-posed as an independent agentic task over the
same papers and graded, by deterministic code, against what the experts
actually decided.

This public repository contains the benchmark contracts and deterministic
verifiers. It does not contain the corpus, answer keys, runs, or scores.

## The five tasks

The tasks are self-contained [Harbor](https://github.com/harbor-framework/harbor)
contracts under `tasks/`, each keeping its grader and floor-regression suite
beside the contract. Query construction itself is not benchmarked: screening
agents start from a frozen candidate pool, never from a live database query.
Per task, inputs ⇒ output ⇒ verifier — each links to the exact
instruction the agent receives:

- **Filter · [`title_abstract_screening`](tasks/title_abstract_screening/steps/screen/instruction.md)**
  — titles and abstracts from a frozen search pool + the review's eligibility
  criteria ⇒ include/exclude per record (`decisions.json`) ⇒ asymmetric
  chance-corrected agreement that makes missed candidates cost ten times extras.
- **Filter · [`full_text_screening`](tasks/full_text_screening/steps/screen/instruction.md)**
  — full OCR of each candidate paper + the review's eligibility criteria ⇒
  include/exclude per study (`decisions.json`) ⇒ the same asymmetric,
  chance-corrected agreement against the review's screening record.
- **Extract · [`full_text_extraction`](tasks/full_text_extraction/steps/extract/instruction.md)**
  — OCR'd included papers + result-free review context; the agent infers which
  outcomes are in scope ⇒ per-arm numeric facts and study characteristics
  (`extractions.json`) ⇒ value-first matched F1, where a value that contradicts
  the paper counts as ten spurious rows — fabrication scores far worse than
  honest omission.
- **Analyze · [`risk_of_bias`](tasks/risk_of_bias/steps/judge/instruction.md)**
  — OCR'd papers + the methodology rubric ⇒ a low/unclear/high judgment per
  bias domain, keyed by study and outcome (`judgements.json`) ⇒ linear-weighted Cohen's kappa against expert
  judgments; chance correction makes every single-label shortcut net zero.
- **Analyze · [`meta_analysis`](tasks/meta_analysis/steps/meta/instruction.md)**
  — raw per-study arm rows + the review's method choices, with no pre-computed
  effects or weights ⇒ pooled estimate, 95% CI, and I² per analysis
  (`analyses.json`) ⇒ point-and-CI agreement within tolerance.

`tasks/smoke/` is a minimal Harbor wiring check, not a benchmark stage.

## What is and isn't here

This repository holds task contracts, graders, and docs, and nothing that
reconstructs an answer key:

- `tasks/<task>/` has the instruction the agent receives
  (`steps/<step>/instruction.md`), the grader (`tests/grade.py`), and a
  floor-regression suite that pins every degenerate shortcut below genuine
  work; each `tests/README.md` lists the floors it pins. The
  `steps/<step>/solution/solve.sh` hook only copies an answer file that a
  private instance stages, so the template carries no answers of its own.
- `docs/` describes each task as inputs ⇒ output ⇒ verifier
  ([Task contracts](docs/tasks.md)), the measurement claims
  ([Methodology](docs/methodology.md)), and the rights boundary
  ([Provenance](docs/provenance.md)).
- `datasets/metapsy/resources/rob/` is the risk-of-bias guidance staged to
  agents, our own restatement of the
  [Metapsy RoB handbook](https://www.metapsy.org/rob/handbook/).

Papers, review corpora, curated reference answers, materialized instances,
oracle replays, and benchmark runs are kept private. A Cochrane or Metapsy
review publishes its own data, so naming the reviews an instance draws on would
hand its answers to anyone who downloads them; keeping instances private is
what keeps the benchmark measuring the work rather than the lookup.

## Why train against it

- **Text in, text out.** Every task is files-in, JSON-out: OCR'd papers staged
  on disk, one structured output file graded by code. No browsing, no search
  API, no tool-use variance — exactly the shape a verifiable-reward RL
  environment needs.
- **Deterministic verifiers.** Reference answers are expert-authored.
  Screening, risk of bias, and meta-analysis are graded entirely in code;
  extraction matches facts in code, then an LLM judge checks that the outcome
  labels on matched facts are semantically equivalent. Every degenerate
  shortcut (include-everything, extract-nothing, one-label-for-all) is pinned
  below genuine work by regression tests, and mutation tests prove the suite
  catches weakened graders.
- **Long context, structurally.** One instance stages tens to hundreds of full
  OCR'd papers — more than fits in a context window, with no retrieval index to
  hide behind. Long-document work, not needle-in-a-haystack recall.
- **Forced decomposition.** No stage can be one-shotted: the agent must
  partition the corpus, brief subagents that cannot see the original
  instruction, and reconcile their outputs into one complete, schema-exact
  file. The four stages themselves are the decomposition every deep-research
  agent depends on.

## Checks

The graders and their floor tests run without a corpus, a model, or the network:

```bash
uv sync --frozen
uv run --frozen python -m pytest -q   # graders, floor regressions, public boundary
bash scripts/sabotage.sh               # floor tests catch weakened graders
```

`scripts/tests/test_public_boundary.py` fails if anything answer-bearing is
tracked, by filename, directory, or JSON key, or if `datasets/` holds anything
beyond the RoB guidance.

## Citations

Tasks run on the [Harbor](https://github.com/harbor-framework/harbor) agent
evaluation framework.

Task designs derive from published Cochrane systematic reviews; see
[Provenance](docs/provenance.md).

Benchmark instances also build on the open meta-analytic trial databases of the
[Metapsy project](https://www.metapsy.org/)
([metapsy-project](https://github.com/metapsy-project) on GitHub). The pinned
database releases used, cited in the form each database requests:

- Kim Setkowski, Christina Palantza, Wouter van Ballegooijen, Renske Gilissen,
  Matthijs Oud, Ioana Cristea, Hisashi Noma, Toshi Furukawa, Arnoud Arntz,
  Anton van Balkom, & Pim Cuijpers (2023). _Database of borderline personality
  disorder trials comparing psychological interventions with control
  conditions. Part of the Metapsy project_ (Version 23.0.1). URL
  [docs.metapsy.org/databases/borderline-psyctr](https://docs.metapsy.org/databases/borderline-psyctr).
  DOI [10.5281/zenodo.10185551](https://doi.org/10.5281/zenodo.10185551).
- Pim Cuijpers, Clara Miguel, Marketa Ciharova, David Ebert, Mathias Harrer, &
  Eirini Karyotaki (2022). _Database of transdiagnostic psychotherapy trials
  for depression and anxiety. Part of the Metapsy project_ (Version 22.0.5).
  URL
  [docs.metapsy.org/databases/depression-anxiety-transdiagnostic](https://docs.metapsy.org/databases/depression-anxiety-transdiagnostic).
  DOI [10.5281/zenodo.7243836](https://doi.org/10.5281/zenodo.7243836).
- Pim Cuijpers, Clara Miguel, Mathias Harrer, Constantin Yves Plessen, Marketa
  Ciharova, & Eirini Karyotaki (2023). _Database of depression psychotherapy
  trials in children & adolescents with control conditions. Part of the
  Metapsy project_ (Version 23.0.2). URL
  [docs.metapsy.org/databases/depression-childadol-psyctr](https://docs.metapsy.org/databases/depression-childadol-psyctr).
  DOI [10.5281/zenodo.8096828](https://doi.org/10.5281/zenodo.8096828).
- Emma Motrico, Irene Gómez-Gómez, Carlos Barquero-Jimenez, Alessia Caffieri,
  Paula de-Juan-Iglesias, Lennert Goossens, Isabel Caceres, Rosalba Company
  Córdoba, Pim Cuijpers, Mathias Harrer, & Clara Miguel (2026). _Database of
  perinatal depression trials comparing psychological intervention with
  control conditions. Part of the Metapsy project_ (Version 26.0.1). URL
  [docs.metapsy.org/databases/depression-perinatal-psyctr](https://docs.metapsy.org/databases/depression-perinatal-psyctr).
  DOI [10.5281/zenodo.18378280](https://doi.org/10.5281/zenodo.18378280).
- S. Parker Singleton, Brooke L. Sevchik, Analiese Lahey, Megan Jones, Sandeep
  M. Nayak, Eric C. Strain, Simon N. Vandekar, Robert H. Dworkin, J. Cobb
  Scott, & Theodore D. Satterthwaite (2026). _Sypres database of depression
  trials comparing psilocybin-assisted therapy with control conditions. Part
  of the Metapsy project_ (Version 26.0.0). URL
  [docs.metapsy.org/databases/depression-psiloctr](https://docs.metapsy.org/databases/depression-psiloctr).
  DOI [10.5281/zenodo.15714852](https://doi.org/10.5281/zenodo.15714852).
- Pim Cuijpers, Clara Miguel, Mathias Harrer, Constantin Yves Plessen, Marketa
  Ciharova, David Ebert, & Eirini Karyotaki (2025). _Database of depression
  psychotherapy trials with control conditions. Part of the Metapsy project_
  (Version 24.0.2). URL
  [docs.metapsy.org/databases/depression-psyctr](https://docs.metapsy.org/databases/depression-psyctr).
  DOI [10.5281/zenodo.7254845](https://doi.org/10.5281/zenodo.7254845).
- Lingyao Tong, Olga-Maria Panagiotopoulou, Clara Miguel, Pim Cuijpers, &
  Eirini Karyotaki (2024). _Database of trials comparing self-guided
  depression interventions with control conditions. Part of the Metapsy
  project_ (Version 24.0.3). URL
  [docs.metapsy.org/databases/depression-selfguided-psyctr](https://docs.metapsy.org/databases/depression-selfguided-psyctr).
  DOI [10.5281/zenodo.12705748](https://doi.org/10.5281/zenodo.12705748).
- Jake Linardon, Aaron Keshen, Clara Miguel, Mathias Harrer, Tara Donker, & Pim
  Cuijpers (2025). _Database of eating disorder trials comparing cognitive
  behavioral interventions with control conditions. Part of the Metapsy
  project_ (Version 25.0.0). URL
  [docs.metapsy.org/databases/ed-psyctr](https://docs.metapsy.org/databases/ed-psyctr).
  DOI [10.5281/zenodo.15663216](https://doi.org/10.5281/zenodo.15663216).
- Rory A. Pfund (2026). _Database of psychological interventions for problem
  gambling and gambling disorder trials with control conditions. Part of the
  Metapsy project_ (Version 26.0.1). URL
  [docs.metapsy.org/databases/gambling-psyctr](https://docs.metapsy.org/databases/gambling-psyctr).
  DOI [10.5281/zenodo.8115993](https://doi.org/10.5281/zenodo.8115993).
- Davide Papola (2024). _Database of GAD trials comparing psychological
  interventions with control conditions. Part of the Metapsy project_
  (Version 23.0.4). URL
  [docs.metapsy.org/databases/gad-psyctr](https://docs.metapsy.org/databases/gad-psyctr).
  DOI [10.5281/zenodo.10185216](https://doi.org/10.5281/zenodo.10185216).
- Yingying Wang, Clara Miguel, Marketa Ciharova, Arpana Amarnath, Jingyuan Lin,
  Ruiying Zhao, Marieke B.J. Toffolo, Sascha Y. Struijs, Leonore M. de Wit, &
  Pim Cuijpers (2024). _Database of OCD trials comparing psychological
  interventions with control conditions. Part of the Metapsy project_
  (Version 24.0.1). URL
  [docs.metapsy.org/databases/ocd-psyctr](https://docs.metapsy.org/databases/ocd-psyctr).
  DOI [10.5281/zenodo.10471942](https://doi.org/10.5281/zenodo.10471942).
- Davide Papola (2023). _Database of panic disorder psychotherapy trials with
  control conditions. Part of the Metapsy project_ (Version 23.0.1). URL
  [docs.metapsy.org/databases/panic-psyctr](https://docs.metapsy.org/databases/panic-psyctr).
  DOI [10.5281/zenodo.7863722](https://doi.org/10.5281/zenodo.7863722).
- Soledad Quero, Sara Fernández-Buendia, Jorge Grimaldos, Laura de la
  Coba-Cañizares, & Clara Miguel (2025). _Database of prolonged grief trials
  comparing psychological interventions with control conditions. Part of the
  Metapsy project_ (Version 25.0.4). URL
  [docs.metapsy.org/databases/grief-psyctr](https://docs.metapsy.org/databases/grief-psyctr).
  DOI [10.5281/zenodo.15538811](https://doi.org/10.5281/zenodo.15538811).
- Edel Mc Glanaghy, David Turner, Georgina A. Davis, Helen Sharpe, Nadine
  Dougall, Paul Morris, Wendy Prentice, & Paul Hutton (2023). _Database of
  randomized clinical trials comparing psychological interventions for
  schizophrenia and psychosis with control conditions. Part of the Metapsy
  project_ (Version 23.1.4). URL
  [docs.metapsy.org/databases/psychosis-psyctr](https://docs.metapsy.org/databases/psychosis-psyctr).
  DOI [10.5281/zenodo.7782324](https://doi.org/10.5281/zenodo.7782324).
- Brooke L. Sevchik, S. Parker Singleton, Analiese Lahey, Megan Jones, Sandeep
  M. Nayak, Eric C. Strain, Simon N. Vandekar, David B. Yaden, Robert H.
  Dworkin, J. Cobb Scott, & Theodore D. Satterthwaite (2026). _Sypres database
  of PTSD trials comparing MDMA-assisted therapy with control conditions. Part
  of the Metapsy project_ (Version 26.0.1). URL
  [docs.metapsy.org/databases/ptsd-mdmactr](https://docs.metapsy.org/databases/ptsd-mdmactr).
  DOI [10.5281/zenodo.18740439](https://doi.org/10.5281/zenodo.18740439).
- National Center for PTSD, US Department of Veterans Affairs (2023). _Database
  of PTSD trials comparing psychological interventions with control
  conditions. Part of the Metapsy project_ (Version 23.0.3). URL
  [docs.metapsy.org/databases/ptsd-psyctr](https://docs.metapsy.org/databases/ptsd-psyctr).
  DOI [10.5281/zenodo.10027042](https://doi.org/10.5281/zenodo.10027042).
- Nino de Ponti, Minoo Matbouriahi, Pamela Franco, Mathias Harrer, Clara
  Miguel, Davide Papola, Ayşesu Sicimoğlu, Pim Cuijpers, & Eirini Karyotaki
  (2024). _Database of social anxiety disorder trials comparing psychological
  interventions with control conditions. Part of the Metapsy project_
  (Version 24.0.1). URL
  [docs.metapsy.org/databases/sad-psyctr](https://docs.metapsy.org/databases/sad-psyctr).
  DOI [10.5281/zenodo.12726122](https://doi.org/10.5281/zenodo.12726122).

## Repository map

```text
README.md
LICENSE
pyproject.toml
docs/                       task contracts, methodology, and provenance
scripts/                    sabotage runner and the public-boundary test
datasets/
  metapsy/resources/rob/    agent-facing risk-of-bias guidance
tasks/
  smoke/
  title_abstract_screening/
  full_text_screening/
  full_text_extraction/
  risk_of_bias/
  meta_analysis/
```

The guiding principle is **the data is the spec**: when a plan disagrees with
what the source review actually did, the source review wins.
