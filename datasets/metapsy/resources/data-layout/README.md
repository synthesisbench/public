# MetaPsy data layout

This is a local, implementation-oriented summary of the MetaPsy data-preparation documentation and its linked template/tool references. It describes the public release package, not this repository's benchmark layout. Source material was retrieved on **2026-07-19**.

## Release package

Each released database has its own public repository in the `metapsy-project` GitHub organization. The repository is named `data-<shorthand>`; for example, a shorthand of `depression-psyctr` gives `data-depression-psyctr`.

The documented core tree is:

```text
data.csv
license
readme.md
metadata/
  authors.json
  last_search.txt
  number_studies.txt
  search_flow.json
  search_string.txt
  shorthand.txt
  variable_description.json
```

Repositories may contain additional files. The files above are the standard data, documentation, licensing, and metadata interface. Exact data columns and metadata members are catalogued in [METADATA.md](./METADATA.md).

## Preparation and publication flow

1. Maintain a database of randomized controlled trials (RCTs).
2. For larger databases, typically partition the database into narrower scientific use files (SUFs), such as trials for a particular indication and comparison.
3. Represent each SUF as a rectangular, wide table and normalize it to the MetaPsy naming, missing-value, and file-format rules.
4. Validate the table. The documentation points to the MetaPsy data-validator application; `metapsyTools::checkDataFormat()` checks required columns and R classes, while `calculateEffectSizes()` or the validator creates the dot-prefixed analysis columns.
5. Assemble `data.csv`, the core `metadata/` files, `license`, and `readme.md` in the database's GitHub repository.
6. Publish a GitHub release from `master`/`main`. GitHub-Zenodo integration assigns a version-specific DOI and a concept/database DOI that resolves to the latest version. The release then feeds the MetaPsy documentation, `metapsyData`, and API.

## `data.csv`: row and table granularity

The table is wide rather than normalized into separate study, arm, outcome, and effect tables. One row represents the results of one trial-arm comparison in one study.

- A two-arm RCT with one relevant outcome contributes one row.
- A multi-arm RCT with `a` arms can have `a! / (2! (a - 2)!)` unique pairwise arm comparisons; the documentation says there is *typically* one row for each included unique comparison.
- A trial with multiple relevant outcomes contributes multiple rows, one per represented outcome.
- `study` therefore does not identify a row. `.id` is the documented unique comparison/row identifier.

The identifier components used by `calculateEffectSizes()` default to `study`, `outcome_type`, `instrument`, `time`, `time_weeks`, and `rating`, plus both arm condition and multi-arm specification fields. The linked current implementation concatenates those values with underscores, replaces commas with underscores, and removes spaces. That implementation detail is not stated as a stable storage contract, so consumers should still treat the stored `.id` as opaque.

Each row supplies one applicable effect-input family: continuous endpoint data, within-group change data, dichotomous data, pre-calculated Hedges' `g`, or a pre-calculated log-risk ratio. Other effect-input families are `NA` in that row. The generated dot-prefixed columns hold standardized effect results and event/sample-size outputs for downstream MetaPsy tooling.

## File and value rules

- Final data is `data.csv`, using a semicolon (`;`) field separator and a comma decimal mark (`1,02`). This corresponds to R's `write.csv2()` format.
- Missing values are the literal `NA`.
- Variable names use `snake_case`, start with a letter, and contain no special characters. A leading underscore is forbidden; a leading dot is reserved for `metapsyTools` variables.
- Semicolons are forbidden in variable names and cell content.
- Character values have no leading or trailing whitespace.
- Metadata is machine-readable JSON or text. `readme.md` is Markdown, and `license` is license text or a persistent license identifier.
- Excel is accepted as a preparation-stage format; CSV conversion is required for public release.

## Validation contract

The data-preparation page says validators check compatibility with the MetaPsy infrastructure after upload. The linked validator web application did not expose readable page text during retrieval, so the inspectable validation details come from the current `metapsyTools` reference:

- `checkDataFormat()` verifies that its default `must.contain` columns exist.
- It verifies the configured R classes and attempts conversion when a class differs.
- Its default contract requires the study/arm/outcome descriptors plus the continuous and dichotomous input columns listed as **validator-required** in [METADATA.md](./METADATA.md).
- `calculateEffectSizes()` uses adequate raw or pre-calculated inputs to append the standard dot-prefixed outputs. Its reference says custom effect-size functions must return all nine documented output columns, although individual values may be `NA`.
- The package reference demonstrates the pipeline `checkDataFormat()` → `checkConflicts()` → `calculateEffectSizes()`; the returned data can then be analyzed by MetaPsy tooling.

Validation should also enforce the lexical CSV and naming rules above and the core repository tree. The checked pages do not publish a single JSON Schema, CSV schema, or complete validator error catalogue.

## How the files connect

- `metadata/shorthand.txt` is the stable retrieval name used by `metapsyData` and the suffix in the GitHub repository name.
- `metadata/variable_description.json` maps `data.csv` column names to database-specific explanations, including factor-level meanings. It is the companion dictionary for both standard and extra columns.
- `metadata/number_studies.txt` counts studies, not rows; row count can be larger because a study can yield multiple comparisons or outcomes.
- `metadata/search_flow.json`, `metadata/search_string.txt`, and `metadata/last_search.txt` document evidence discovery and selection for the current database version.
- `metadata/authors.json` identifies database authors/owners and their ORCID identifiers.
- Root `readme.md` summarizes the database and carries its DOI badge; the same text is shown on Zenodo.
- Root `license` controls reuse. The documented default is the **Open Data Commons Attribution License (ODC-By) v1.0**. A specific repository can instead carry another license, so read that repository's `license` file rather than assuming the default.

## Documented ambiguities and observed mismatches

- The Data Format page says its study-design, effect-input, and nine dot-prefixed variables are included in every database. The current `checkDataFormat()` default requires a narrower 20-column subset and does not default-require `full_ref`, change-score inputs, pre-calculated inputs, or dot-prefixed outputs. [METADATA.md](./METADATA.md) preserves both claims.
- The Data Format page documents `rating` values as `self-report` and `clinician`; the linked template CSV uses `self-reported` in example rows. This reference treats the documentation page as normative and records the template mismatch rather than adding a third allowed value.
- The linked template is explicitly demonstration/test data. Its `data.csv` includes database-specific fields, an unnamed first column, omits the standard-page `full_ref` field, and contains both arm orderings for example comparisons even though the format page says there is *typically* one row per unique arm comparison. These observations are not promoted to core schema rules.
- The template's `search_flow.json` supplies exact current keys, but the documentation defines exclusion-reason labels as database-specific and does not define every key's semantics beyond its name.
- The downloadable Excel example returned HTTP 200 with the expected XLSX media type, but the documentation browser could not render its contents. Its schema was therefore not used as an additional authority.
- Several documentation pages display implausible update dates such as `01 Jan 0001`; the retrieval date above records when this snapshot was checked, not when MetaPsy last revised each page.

## Sources

Retrieved **2026-07-19**. The first four pages are the complete Data Preparation section discovered through its sidebar and previous/next navigation; the remaining pages are linked references used to resolve layout, validation, release, identifiers, examples, and licensing.

- <https://docs.metapsy.org/data-preparation/>
- <https://docs.metapsy.org/data-preparation/format/>
- <https://docs.metapsy.org/data-preparation/metadata/>
- <https://docs.metapsy.org/data-preparation/upload/>
- <https://github.com/metapsy-project/data-template>
- <https://github.com/metapsy-project/data-template/tree/master/metadata>
- <https://raw.githubusercontent.com/metapsy-project/data-template/master/data.csv>
- <https://raw.githubusercontent.com/metapsy-project/data-template/master/metadata/authors.json>
- <https://raw.githubusercontent.com/metapsy-project/data-template/master/metadata/last_search.txt>
- <https://raw.githubusercontent.com/metapsy-project/data-template/master/metadata/number_studies.txt>
- <https://raw.githubusercontent.com/metapsy-project/data-template/master/metadata/search_flow.json>
- <https://raw.githubusercontent.com/metapsy-project/data-template/master/metadata/search_string.txt>
- <https://raw.githubusercontent.com/metapsy-project/data-template/master/metadata/shorthand.txt>
- <https://raw.githubusercontent.com/metapsy-project/data-template/master/metadata/variable_description.json>
- <https://raw.githubusercontent.com/metapsy-project/data-template/master/license>
- <https://raw.githubusercontent.com/metapsy-project/data-template/master/readme.md>
- <https://docs.metapsy.org/uploads/example-metapsy-formatted-dataset.xlsx>
- <https://tools.metapsy.org/reference/checkdataformat>
- <https://tools.metapsy.org/reference/calculateeffectsizes>
- <https://raw.githubusercontent.com/metapsy-project/metapsyTools/master/R/calculateEffectSizes.R>
- <https://tools.metapsy.org/data-validator>
- <https://tools.metapsy.org/articles/metapsytools>
- <https://docs.metapsy.org/databases/>
- <https://docs.metapsy.org/release/>
- <https://opendatacommons.org/licenses/by/1-0/>
