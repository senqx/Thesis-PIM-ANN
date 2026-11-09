# Current findings

Current evidence is generated under `results/` and discussed in the
[thesis](../../doc/pim_ann_thesis.pdf). The ten-split paired cycle comparison is
[paired_summary.csv](../../results/paired_summary.csv).

At the default configuration, query-aware placement uses about 0.31% fewer cycles
than BFS for 512-byte vectors, and about 0.17% more for the hypothetical 128-byte
footprint. The smaller footprint retains float32 traversal and does not establish
quantised-search accuracy or performance. Controller sensitivities can change
these comparisons. The study establishes no optimality bound and no PIM speedup.

The earlier negative-result explanation and timing numbers are invalidated and
preserved only in `archive/pre-review/sprint1/docs/findings.md`.
