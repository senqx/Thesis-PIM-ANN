# Immutable source snapshots

`pre-change/` contains exact original native source and documentation. Historical
analysis, reporting and artifact scripts are in
[the script archive](../../../scripts/archive/pre-change/).
The historical manifest verifies these copies in place of modified working
files. Relative links inside an immutable Markdown snapshot retain their
original directory context; use the [current study index](../README.md) to
navigate. The original full manuscript and repository are also preserved at
[commit c729a67](https://github.com/senqx/Thesis-PIM-ANN/tree/c729a67).

Banners and navigation belong outside these files so their hashes remain exact.

## Checkpoint before direct feasibility checks

[pre-direct.zip](pre-direct.zip) preserves the derived corrected artifact,
its exact analysis/verifier/report/test sources, the independent review, and the
corresponding thesis source/PDF/build record from `898052a`. Members use paths
relative to the repository root. Large unchanged native samples, input tables,
kernels and simulator archives remain shared rather than duplicated. The archived
corrected manifest verifies those shared files and the preserved derived files.

`python3 scripts/review_decision_costs.py` checks that manifest using archived
members first and shared files otherwise, then reproduces the historical review
JSON. The current corrected verifier also checks the preserved checkpoint and
confirms all original choices and model prediction timings remain unchanged.

For an isolated runnable copy of the complete prior repository, use:

```sh
git worktree add --detach /tmp/thesis-before-direct 898052a
cd /tmp/thesis-before-direct
python3 scripts/decision_correction.py verify
```

The current report uses the direct-rule revision. This checkpoint is retained
for provenance, not an additional set of independent measurements.
