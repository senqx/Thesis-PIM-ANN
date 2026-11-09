# Final research pass

This record separates completed repairs, additional evidence, and deliberately
unevaluated questions. It supplements `REVIEW_FIXES.md`; it does not change the
primary experiment after seeing a preferred result.

## Bounded experiment design

The following settings were selected from the exploratory matrix before examining
the new repeated results. The earlier first split remains part of the ten-split
estimate, so this is a robustness extension, not an independent confirmatory study.

* Repeat outstanding-limit one, ClosedCAP cap four, and alternate address mapping
  on the same ten splits, for all five layouts and both footprints: 300 replays.
  Compare against BFS within each setting and split. Keep the other controller
  and heuristic settings explicitly exploratory, with one split each.
* Add graph seeds 101 and 102 in corpus insertion order, plus graph seed 100 with
  insertion-order seed 17. Evaluate each on query splits one through three, all
  layouts and both footprints: 90 replays. Preserve original corpus IDs, the same
  exact-neighbour universe, and matching train/test IDs. Compare layouts within
  each graph. Show means and observed ranges over the three query splits; do not
  pool the selected graphs into a supposed population confidence interval.
* Record all nine supported HBM2 command counts for the 128-byte BFS/query-aware
  comparison, under outstanding limits one and 64, for mixed, vector-only, and
  adjacency-only streams: 12 diagnostic replays. Removing one request type changes
  scheduling; the component timings must not be added to predict mixed timing.
* Record command counts and cycle/address command traces for sequential/permuted
  microbenchmarks with outstanding limits one and 64: four replays. Attribute
  command versus no-command cycles exactly, and measure bank diversity in fixed
  request windows. Do not call every no-command cycle a DRAM timing stall.

The 406 new replays supplement the original 385, for 791 retained timing results.
Regenerating all ten primary streams checks that the insertion-order support has
not changed the existing experiment. The simulator binary and timing model remain
the same; command recording uses the pinned simulator's observer plugins.

## Completion criteria — satisfied

* Reject missing prerequisite traces before starting sensitivity work.
* Validate cache contents, sidecar files, input identity and output hashes.
* Check every expected experiment by name, not only a total file count.
* Verify independent-index agreement for both insertion orders and exact recall
  within each constructed graph; preserve primary trace hashes.
* Explain the experiment chain, unfamiliar terms, metric denominators, mechanisms,
  uncertainty, and practical effect size in both documents.
* Build both PDFs, inspect figures/tables, and update the validation record with
  actual outcomes rather than this prospective checklist.

## Observed outcome

All 791 named replay records pass validation. At 512 bytes the query-aware layout
beats BFS in every tested graph/split pair. At 128 bytes, graph seeds 101 and 102
reverse the original graph's loss, and shuffled insertion gives mixed split-level
signs. The three repeated controller settings retain their conditional signs
across all ten query splits. These observations reinforce the need to evaluate the
constructed graph and memory assumptions together.

The source, correctness, sanitizer, clean-build and document checks are recorded in
[VALIDATION.md](VALIDATION.md). The [reading guide](READING_GUIDE.md) provides a path
through the explanations and evidence.

## Questions outside the completed scope

Other real datasets/corpus subsets, HNSW operating points, dependent execution,
caches, real quantisation, deployed mapping costs, energy, workload drift and an
integrated PIM implementation remain future work. The thesis claims conditional
DRAM-stream characterisation. None of these missing experiments is evidence of
an application speedup or a universal layout winner.
