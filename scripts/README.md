# scripts/

| File | Role |
| --- | --- |
| `sabotage.sh` | Breaks each grader on purpose, one constant at a time, and requires the named floor test to go red. A green suite proves nothing by itself; a mutation nothing catches is a floor nobody guards. |
| `tests/test_public_boundary.py` | Asks Git what is tracked and fails on anything gold-bearing by name, directory, or JSON key, and on any file under `datasets/` other than `metapsy/resources/`. `.gitignore` alone can't hold this line, because its globs are path-shaped and silently stop matching when a layout nests one level deeper. |

Run both with `uv run --frozen python -m pytest` and `bash scripts/sabotage.sh`.
