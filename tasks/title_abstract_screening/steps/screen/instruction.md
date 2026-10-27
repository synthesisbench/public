# Title-Abstract Screening

You are doing a local title abstract screening stage for this review dataset. Use
only the files staged under `/task`; do not use the web or any external sources.

A pool of candidate studies (study_id, title, authors, journal, year) is in
`/task/screen_in.json`. Each candidate study has its abstract staged under
`/task/papers/`; `/task/papers/index.json` maps each `study_id` to its markdown
path or paths. The filenames use the study slug: the `study_id` lowercased with
non-alphanumeric runs replaced by hyphens.

Refer to `/task/criteria.md` for the review's **eligibility (PICO) criteria** —
its objectives, the criteria for considering studies (study design,
participants, interventions), and the pre-specified outcomes.

Reference materials may be staged under `/task/resources/`. If present, use
them as general methodology guidance. They are general references and
contain nothing specific to this review.

Judge each study's abstract against the criteria before deciding
whether to **include** it (after title abstract assessment) or **exclude**
it.

The task list can run long, and each study carries an abstract. Delegate deliberately to subagents.
A subagent only sees what you give it — it cannot read this file.

Write `/task/decisions.json` as:

```json
{"decisions": {"<study_id>": "include" | "exclude", "...": "..."}}
```

Every study in the pool must appear exactly once.
