# synthesis-bench/smoke

A throwaway task whose only job is to prove the Harbor evaluation loop runs end to
end and the Oracle scores `1.0`. This is the "grade the graders" discipline as the
first commit — if Oracle isn't green here, paths/wiring are wrong before any real
data is involved.

## What the agent does

Writes the exact text `smoke-ok` to `/app/answer.txt`. See
[`instruction.md`](instruction.md).

## Environment

- Base image: `ubuntu:24.04` (see [`environment/Dockerfile`](environment/Dockerfile))
- No extra packages — the verifier is pure shell, no network.
- Agent timeout: 600s.

## Verifier

Custom shell ([`tests/test.sh`](tests/test.sh)), shared environment (runs in the
agent container). Deterministic, single criterion:

| Check | Type | Reward |
| --- | --- | --- |
| `/app/answer.txt` equals `smoke-ok` | programmatic (string equality) | `1` pass / `0` fail |

Writes the score to `/logs/verifier/reward.txt`.

## Layout

```
smoke/
├── task.toml                 # config + metadata
├── instruction.md            # agent prompt
├── environment/Dockerfile    # ubuntu:24.04, no extras
├── solution/solve.sh         # Oracle reference solution
└── tests/test.sh             # custom-shell verifier → reward.txt
```

## Running

```bash
# Oracle (must return reward 1.0)
harbor run -p tasks/smoke -a oracle

# Inspect trajectories / reward details
harbor view jobs

# A real agent (optional)
harbor run -p tasks/smoke -a terminus-2 -m anthropic/claude-sonnet-4-6
```
