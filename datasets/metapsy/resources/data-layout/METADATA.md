# MetaPsy data and metadata dictionary

This dictionary records the exact public field names documented for the MetaPsy release format. Source material was retrieved on **2026-07-19**. “Not stated” means the checked sources do not document the type, allowed-value set, or requiredness; no type is inferred from a field's name.

## Reading presence and type

- **Standard**: the Data Format page says the column belongs to the standard variables included in every MetaPsy database.
- **Validator-required**: the column also appears in the default `must.contain` argument of `metapsyTools::checkDataFormat()`.
- **Conditional value**: the column is present, but a row uses it only when that effect-input family or multi-arm case applies; otherwise the value is `NA`.
- Types shown as **R character** or **R numeric** are the classes in the current `checkDataFormat()` default `variable.class` list. They describe the parsed R table, not a separately published on-disk CSV type system.

## `data.csv` study and comparison columns

| Field | Presence | Documented type / values | Meaning |
|---|---|---|---|
| `study` | Standard; validator-required | R character; format `First-author surname, year` | Study label, for example `Smith, 2011`. It is not row-unique. |
| `condition_arm1` | Standard; validator-required | R character; controlled labels are standardized across trials, but the allowed set is not published here | Condition in trial arm 1; `cbt` is an example. |
| `condition_arm2` | Standard; validator-required | R character; controlled labels are standardized across trials, but the allowed set is not published here | Condition in trial arm 2; `wlc` is an example. |
| `multi_arm1` | Standard; validator-required; conditional value | R character; `NA` when the study is not multi-arm | More specific treatment/condition label for arm 1 in a multi-arm trial; examples include `f2f` and `Internet`. |
| `multi_arm2` | Standard; validator-required; conditional value | R character; `NA` when the study is not multi-arm | More specific treatment/control label for arm 2 in a multi-arm trial; examples include `wl` and `plac`. The column remains present even when its value repeats across comparisons. |
| `outcome_type` | Standard; validator-required | R character; examples `response`, `remission`, `deterioration`; `msd` is typical for mean/SD outcomes. The examples are not documented as exhaustive. | Kind of outcome underlying the comparison; for dichotomous data, identifies what the event count means. |
| `instrument` | Standard; validator-required | R character; allowed identifiers not specified | Instrument used to measure the outcome. |
| `time` | Standard; validator-required | R character; examples `post`, `follow-up`, not documented as exhaustive | Outcome measurement point. |
| `time_weeks` | Standard; validator-required | R numeric; `NA` when unavailable | Weeks from randomization to the measurement point. |
| `rating` | Standard; validator-required | R character; documented values `self-report` and `clinician` | Whether the outcome was self-reported or clinician-rated. The linked example CSV instead contains `self-reported`; that mismatch is not treated as a documented allowed value. |
| `full_ref` | Standard; omitted from the validator's default required list | Type and missingness not stated | Full reference to the main or relevant publication. |

## `data.csv` effect-input columns

Exactly one of groups (a)–(e) is populated for a row according to the reported outcome data; the other groups contain `NA` in that row.

### (a) Continuous endpoint data

| Field | Presence | Documented type | Meaning |
|---|---|---|---|
| `mean_arm1` | Standard; validator-required; conditional value | R numeric | Outcome mean in arm 1 at the measurement point. |
| `mean_arm2` | Standard; validator-required; conditional value | R numeric | Outcome mean in arm 2 at the measurement point. |
| `sd_arm1` | Standard; validator-required; conditional value | R numeric | Outcome standard deviation in arm 1. |
| `sd_arm2` | Standard; validator-required; conditional value | R numeric | Outcome standard deviation in arm 2. |
| `n_arm1` | Standard; validator-required; conditional value | R numeric | Sample size in arm 1. |
| `n_arm2` | Standard; validator-required; conditional value | R numeric | Sample size in arm 2. |

### (b) Within-group change data

| Field | Presence | Documented type | Meaning |
|---|---|---|---|
| `mean_change_arm1` | Standard; conditional value; omitted from validator default | Not stated | Mean change from baseline to the measurement point in arm 1. |
| `mean_change_arm2` | Standard; conditional value; omitted from validator default | Not stated | Mean change from baseline to the measurement point in arm 2. |
| `sd_change_arm1` | Standard; conditional value; omitted from validator default | Not stated | Standard deviation of mean change in arm 1. |
| `sd_change_arm2` | Standard; conditional value; omitted from validator default | Not stated | Standard deviation of mean change in arm 2. |
| `n_change_arm1` | Standard; conditional value; omitted from validator default | Not stated | Sample size for change data in arm 1. |
| `n_change_arm2` | Standard; conditional value; omitted from validator default | Not stated | Sample size for change data in arm 2. |

### (c) Dichotomous data

| Field | Presence | Documented type | Meaning |
|---|---|---|---|
| `event_arm1` | Standard; validator-required; conditional value | R numeric | Event count in arm 1; the event can be response, remission, deterioration, or another outcome identified by `outcome_type`. |
| `event_arm2` | Standard; validator-required; conditional value | R numeric | Event count in arm 2. |
| `totaln_arm1` | Standard; validator-required; conditional value | R numeric | Total sample size in arm 1 for the dichotomous outcome. |
| `totaln_arm2` | Standard; validator-required; conditional value | R numeric | Total sample size in arm 2 for the dichotomous outcome. |

### (d) Pre-calculated Hedges' `g`

| Field | Presence | Documented type | Meaning |
|---|---|---|---|
| `precalc_g` | Standard; conditional value; omitted from validator default | Not stated | Pre-calculated, small-sample-bias-corrected standardized mean difference (Hedges' `g`). |
| `precalc_g_se` | Standard; conditional value; omitted from validator default | Not stated | Standard error of `precalc_g`, equal to the square root of its variance. |

### (e) Pre-calculated log-risk ratio

| Field | Presence | Documented type | Meaning |
|---|---|---|---|
| `precalc_log_rr` | Standard; conditional value; omitted from validator default | Not stated | Pre-calculated natural-log risk ratio comparing events in arm 1 with arm 2. |
| `precalc_log_rr_se` | Standard; conditional value; omitted from validator default | Not stated | Standard error of `precalc_log_rr`. |

## `data.csv` generated `metapsyTools` columns

These nine standard fields are created by `calculateEffectSizes()` or the data validator. The Data Format page says they are included for immediate use by `metapsyTools`. The `calculateEffectSizes()` reference says its effect-size-function output must include all nine columns, although values may be `NA`; `checkDataFormat()` does not default-require them.

| Field | Documented type / values | Meaning / relationship |
|---|---|---|
| `.id` | Character in the linked current implementation; unique | Unique trial-arm-comparison/row identifier. The default construction concatenates `study`, `outcome_type`, `instrument`, `time`, `time_weeks`, `rating`, both `condition_arm*` fields, and both `multi_arm*` fields with underscores, then replaces commas with underscores and removes spaces. This is current implementation behavior, not a separately stated stable schema guarantee; treat stored IDs as opaque. |
| `.g` | Not stated; may be `NA` | Calculated Hedges' `g`. |
| `.g_se` | Not stated; may be `NA` | Standard error of `.g`. |
| `.log_rr` | Not stated; may be `NA` | Calculated natural-log risk ratio. |
| `.log_rr_se` | Not stated; may be `NA` | Standard error of `.log_rr`. |
| `.event_arm1` | Not stated; may be `NA` | Output event count for arm 1. |
| `.event_arm2` | Not stated; may be `NA` | Output event count for arm 2. |
| `.totaln_arm1` | Not stated; may be `NA` | Output total sample size for arm 1. |
| `.totaln_arm2` | Not stated; may be `NA` | Output total sample size for arm 2. |

The current `calculateEffectSizes()` reference additionally documents optional `.log_rom` and `.log_rom_se` outputs when ratio-of-means calculation is enabled. They are **not** among the nine standard columns listed by the Data Format page, so they are optional tool outputs rather than core fields in this dictionary.

## Additional `data.csv` columns

Database-specific columns are allowed and should be explained in `metadata/variable_description.json`. No universal field list, types, or allowed values are documented for them. They still follow the global rules: `snake_case`, leading letter, no special characters or semicolons, trimmed character values, and `NA` for missing values. A leading dot remains reserved for `metapsyTools` outputs.

## Core repository metadata

| File / member | Presence and type | Definition |
|---|---|---|
| `metadata/authors.json` | Core file; JSON array | Database authors or owners and their ORCID research identifiers. The linked template represents each entry as an object with exact members `name` and `orcid`, both JSON strings. No other member rules are documented. |
| `metadata/authors.json[].name` | Template member; JSON string | Author/owner name, for example `Pim Cuijpers`. |
| `metadata/authors.json[].orcid` | Template member; JSON string | ORCID identifier, represented in the template as four hyphen-separated groups, for example `0000-0001-5497-2743`. The checked page does not state validation rules beyond identifying it as an ORCID. |
| `metadata/last_search.txt` | Core text file; exact `YYYY-MM-DD` date format | Date of the last search update. |
| `metadata/number_studies.txt` | Core text file; count | Number of studies in the current database version. The documentation does not specify lexical constraints beyond “number”; the linked example contains `542`. |
| `metadata/search_string.txt` | Core text file; format otherwise not stated | Search string or strings used to identify records. |
| `metadata/shorthand.txt` | Core text file; allowed characters not stated | Database shorthand used by `metapsyData`; it also supplies the `<shorthand>` part of repository name `data-<shorthand>`. |
| `metadata/variable_description.json` | Core file; JSON object | Dictionary whose keys are exact `data.csv` variable names and whose values explain the variables and, where relevant, factor levels. The template uses JSON strings as values; the page does not publish a schema beyond key-value descriptions. |
| `metadata/search_flow.json` | Core file; JSON object | Search/screening flow counts. Exact linked-template members are listed below. The page says all keys must be specified, with `0` when a step does not apply; its nested exclusion-reasons object is a documented exception to scalar numeric values. |
| `license` | Core root file; license text or persistent identifier | License governing the released data. Default: ODC-By v1.0; a repository may specify another license. |
| `readme.md` | Core root Markdown file | Database topic/content summary shown on GitHub and Zenodo, including a DOI badge populated at final release. |

## `metadata/search_flow.json`

These are the exact keys in the documentation's linked template. The documentation does not separately define them, so the descriptions below are **inferred from the field names**. Exclusion-reason labels are explicitly database-specific and may be freely adapted.

| Exact key | Documented shape / status | Meaning |
|---|---|---|
| `database.hits` | Template key; numeric count | **Inferred:** records returned by database searches before deduplication. |
| `database.hits.duplicates.removed` | Template key; numeric count | **Inferred:** database hits remaining after duplicate removal. Despite the wording “duplicates removed,” the template value equals `records.screened`, so it appears to be a post-deduplication total rather than the number removed. |
| `records.screened` | Template key; numeric count | **Inferred:** records screened. |
| `full.text.assessed.for.eligibility` | Template key; numeric count | **Inferred:** full-text reports assessed for eligibility. |
| `full.text.excluded.reasons` | Template key; JSON object | Maps freely chosen exclusion-reason labels to numeric counts. The labels in the template are examples, not allowed values. |
| `included` | Template key; numeric count | **Inferred:** studies or records included; the documentation does not explicitly state which unit this count uses. |

The page's instruction to use `0` for non-applicable keys is clear for numeric step counts. It does not say whether an inapplicable `full.text.excluded.reasons` should be `{}` or `0`; preserve that ambiguity rather than assuming a representation.

## Cross-file identifiers and cardinality

- `metadata/shorthand.txt` identifies the database/repository; it is not a `data.csv` row key.
- `.id` identifies a comparison row.
- `study` groups rows from the same study, but the documentation does not define a separate canonical study ID.
- `metadata/number_studies.txt` counts studies, so it need not equal the number of rows in `data.csv`.
- `metadata/variable_description.json` keys join to `data.csv` column names.
- `authors.json[].orcid` identifies people; it has no documented relationship to data rows.

## Sources

Retrieved **2026-07-19**.

- <https://docs.metapsy.org/data-preparation/format/>
- <https://docs.metapsy.org/data-preparation/metadata/>
- <https://docs.metapsy.org/data-preparation/upload/>
- <https://tools.metapsy.org/reference/checkdataformat>
- <https://tools.metapsy.org/reference/calculateeffectsizes>
- <https://raw.githubusercontent.com/metapsy-project/metapsyTools/master/R/calculateEffectSizes.R>
- <https://raw.githubusercontent.com/metapsy-project/data-template/master/data.csv>
- <https://raw.githubusercontent.com/metapsy-project/data-template/master/metadata/authors.json>
- <https://raw.githubusercontent.com/metapsy-project/data-template/master/metadata/last_search.txt>
- <https://raw.githubusercontent.com/metapsy-project/data-template/master/metadata/number_studies.txt>
- <https://raw.githubusercontent.com/metapsy-project/data-template/master/metadata/search_flow.json>
- <https://raw.githubusercontent.com/metapsy-project/data-template/master/metadata/search_string.txt>
- <https://raw.githubusercontent.com/metapsy-project/data-template/master/metadata/shorthand.txt>
- <https://raw.githubusercontent.com/metapsy-project/data-template/master/metadata/variable_description.json>
- <https://raw.githubusercontent.com/metapsy-project/data-template/master/license>
- <https://docs.metapsy.org/databases/>
- <https://opendatacommons.org/licenses/by/1-0/>
