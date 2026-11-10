# Placement alternatives and available-request experiment

Design fixed on 10 November 2026, before inspecting these follow-up timing results.

The motivating question is whether natural locality improvements fail only for
our implementation or whether their value changes with the work available to the
controller. We seek useful negative and positive observations, without requiring
either outcome. A failed heuristic is not proof that every method in its class
fails. Repetition estimates variability; it cannot establish a universal theorem.

## Comparisons

1. Add RCM, Gorder and Porder from the **published NeurIPS 2022 supplementary
   artifact** of Coleman et al. Use the supplied layout routines and their
   five-node Gorder/Porder window. Porder weights each base-layer edge by one plus
   the number of training searches that evaluate its destination through that
   edge. All methods permute the same separate vector array; this tests their
   layouts in our memory model and does not reproduce the authors' cache-aware
   application benchmark. Preserve source hashes and describe implementation
   details, including the supplied window-expiration condition. The weighted
   linked-list priority queue is replaced by an ordered set with the same score
   updates and update-recency tie order; compare output permutations against the
   unmodified reference on 30 weighted graphs before the timing campaign.
2. Compare flat replay with expansion-bounded replay. Finish each adjacency
   payload before offering its candidate vectors, and finish those vectors before
   the next adjacency expansion. Initial vectors and consecutive adjacency reads
   also receive separate phases. The simulator's existing draining query marker
   represents a phase; retain an explicit phase-to-original-query map.
3. Inside a candidate-vector phase, compare the original order with address
   sorting and transaction round-robin across vectors. These schedules use only
   the phase's available candidates and preserve every transaction, including
   repeated reads. They do not sort across graph expansions. Evaluate these two
   alternatives on BFS and query-aware placement, with each compared against its
   own original-order, expansion-bounded baseline.

The expansion boundary adds memory dependencies, not distance-computation time,
scratch accesses, caching, mapping traffic, host/PIM communication or an integrated
PIM execution. A positive result remains a simulated memory-service opportunity.
The model assumes candidate vector reads within an expansion can be overlapped;
it is not a cycle-exact simulation of stock hnswlib instruction execution.

## Fixed matrix and interpretation

Use the ten existing reference query splits and the three existing alternative
constructions on splits 1–3: 19 graph/split pairs. Each uses both 512- and 128-byte
footprints, the same HBM2 model, default mapper, open-page controller and maximum
64 outstanding transactions. Keep all original evidence.

For each pair/footprint retain three new flat-layout replays (RCM, Gorder, Porder),
six expansion-bounded original-order replays (identity, BFS, query-aware, RCM,
Gorder, Porder), and four bounded scheduling replays (two schedules on BFS and
query-aware): **494 additional replays**. The first pair is a pipeline pilot and
remains in the final matrix. No method is dropped because of its performance.

Report paired effects over the ten reference splits. Report construction-specific
means and ranges separately, using matched splits. These are exploratory
extensions using previously evaluated query sets, not independent confirmation.
Do not repeatedly add samples until an interval excludes zero. Report comparisons
against identity as well as BFS, and compare scheduling within matching boundaries.

## Required checks

* Rebuilt graphs, split IDs, exact/returned IDs, logical accesses and existing
  vector mappings agree with retained evidence before using new layouts.
* Training IDs remain disjoint from evaluation IDs. Profile weights use only
  training accesses and valid base-layer edges.
* Published layouts are complete permutations. Record the exact source archive,
  extracted headers, build command, wrapper and executable hashes.
* The independent emitter reproduces existing flat trace hashes exactly.
* Every candidate in a phase belongs to the preceding adjacency list, except the
  explicitly separated entry read at a graph-level transition.
* Original, sorted and round-robin schedules have identical transaction multisets
  within every phase. No transaction crosses a phase or original-query boundary.
* All reads complete. Phase timings drain and aggregate back to original queries.
  Retain raw phase timings losslessly compressed, with hashes.
* Validate all expected names and all raw evidence before generating tables.

This campaign answers missing comparisons directly connected to the thesis.
Adding new datasets, full PIM compute or a different ANN algorithm requires a
specific unresolved question; these are not automatic extensions of this matrix.

## Diagnostic addition after the pilot

The first completed case exposed a large round-robin improvement at 512 bytes
and a loss at 128 bytes. To explain that contrast, add **four diagnostic repeats**:
BFS original-order bounded and round-robin replay at each footprint, on reference
split one. Use the existing command-count observer, require exact timing and
phase-sidecar equality with the corresponding main runs, and measure offered bank
diversity in full 64-transaction windows contained within a phase. These are
mechanism observations selected after the pilot, not extra independent samples
or new tuning conditions. Keep the original 494-comparison design unchanged.
The combined artifact therefore contains **1,289 replays**: 791 previous,
494 follow-up comparisons and four scheduling diagnostics.
