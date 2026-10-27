# Provenance

## Source

The task designs derive from published Cochrane systematic reviews and public
MetaPsy databases. This project has no governance or distribution relationship
with either organization. The repository does not redistribute the private
Cochrane corpus or copyrighted trial papers.

## Public contents

This repository contains task contracts, deterministic verifiers, regression
tests, and the risk-of-bias guidance staged to agents (our own restatement of
the [MetaPsy RoB handbook](https://www.metapsy.org/rob/handbook/)). Instances,
answer keys, the curation that builds them, copyrighted trial papers, benchmark
runs, and model scores are not included.

Three rights boundaries remain outside the public tree:

1. published reviews and the decisions recorded in them;
2. constituent trial papers owned by their publishers and journals;
3. licensed methodology material such as risk-of-bias crib sheets and handbook
   text.

The tasks may encode factual conventions needed to define evidence-synthesis work,
but they do not reproduce licensed guidance. Risk-of-bias terminology refers to
[RoB 2](https://www.riskofbias.info/), and statistical conventions refer to the
[Cochrane Handbook](https://training.cochrane.org/handbook).

## Reference isolation

Private builders stage source documents for the agent and human references for the
verifier. The two surfaces are separate by construction: the agent sees `/task`;
the grader reads `/tests/human` or `/tests/gold`. Public task instructions contain
no answer key or rubric description.

## Naming the source

The source organization is named because provenance should be explicit. Naming it
does not imply endorsement, partnership, or permission to distribute its material.

If you are a rights holder and believe this repository crosses a boundary, please
contact the project owner so the material can be reviewed promptly.
