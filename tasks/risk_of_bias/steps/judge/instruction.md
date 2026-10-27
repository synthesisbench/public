# Risk of Bias

You are doing a local risk-of-bias judgement stage for this review dataset. Use
only the files staged under `/task`; do not use the web or any external sources.

The tasks are in `/task/rob_in.json`: the `review_id`, a `framework` field, and a
`tasks` array. Each task has a `study_id`, an `outcome` (already set per task —
`null` for some, a string for others), and the exact `domains` to judge. Copy
each task's `study_id` and `outcome` verbatim into your output; you never need to
reason about the framework yourself.

Each study's full text is under `/task/papers/`.
`/task/papers/index.json` maps each `study_id` to its files. It also
lists the exact `study_id`, paper IDs, and paths to use. `/task/review_context.md`
contains the review objective, eligibility criteria, and pre-specified outcomes.
**Read the paper(s) for a study before judging it**, and base every judgement on
what the paper reports.

Reference materials may be staged under `/task/resources/`. If present, use
them as methodology guidance for interpreting the signalling questions. They
are general references and contain nothing specific to this review.

The task list can run long, and each study carries full text. Delegate deliberately to subagents.
A subagent only sees what you give it — it cannot read this file.

## Labels

Each domain gets exactly one lowercase string: `low`, `unclear`, or `high`.

- `low` — the method is adequately reported AND protects against this bias.
- `unclear` — the method is under-reported, or the concern can't be resolved.
  Use this rather than guessing `low`.
- `high` — the paper shows a concrete flaw creating real bias risk.

No other value is valid. A "some concerns" assessment maps to `unclear`. Never
emit "High risk", "Low", "n/a", etc. Use `low` only when the paper gives enough
methodological detail to support it; when in doubt between `low` and `unclear`,
choose `unclear`.

Judge only the `domains` listed for each task — never add or rename domains.

## Output

Write `/task/judgements.json` as **raw JSON only** — no markdown fences, no
commentary:

```json
{
  "judgements": {
    "<study_id>": {
      "<outcome>": {
        "<domain>": "low"
      }
    }
  }
}
```

- One study key per study and one outcome key per task — cover every task.
- Copy `study_id` and `outcome` **character-for-character** from the task (the
  `outcome` string can be long). When a task's `outcome` is `null`, use the key
  `"study-level"`.
- Each outcome's object must contain **every** listed domain and nothing else,
  each set to `low`, `unclear`, or `high`.
