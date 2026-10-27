# Oracle payload

A committed demo instance must replace the placeholder `extractions.json` with
a populated payload that recovers every verifier-side `extract_facts` record.
It must introduce no extra rows or contradictions.
`solve.sh` copies that instance payload to `/task/extractions.json` unchanged.
The oracle gate is the proof that the demo payload satisfies the full contract.
