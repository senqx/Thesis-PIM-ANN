# Training-based choice of a vector-fetch schedule

This is a separate extension requested on 10 November 2026 after the first
scheduling-sensitivity cases exposed mapping and concurrency reversals. The
360-replay sensitivity design remains unchanged. The proposal is an optional
memory-submission path for a PIM-oriented/near-memory execution frontend capable
of issuing the modelled chunks. It is not a new HNSW search algorithm or a claim
that existing commercial PIM hardware exposes this interface.

## Fixed policy and evaluation

For each target configuration, run original order, address sorting and round-robin
on the first **50 training queries** of that split. Choose the order with the
lowest total simulated service cycles; exact ties prefer original order, then
sorting, then round-robin. Freeze this choice before accessing held-out timings
in the policy evaluator. Use it for every held-out query under that configuration.
Reprofile when the graph/layout, footprint, batch size or memory configuration
changes. A missing/mismatched profile should fall back to original order in an
implementation. The evaluated policy assumes zero extra execution overhead;
deployment must charge profiling, buffering, dispatch and communication costs.

Use BFS on the reference graph, all ten existing splits, both footprints, and
the default plus six fixed sensitivity configurations. This adds **420 calibration
replays** (ten × two × seven × three), each with 50 original training queries.
The fixed 200-query held-out timings already exist in the main campaigns. The
chosen schedule's replay is its exact measured request stream, so policy evaluation
reuses that record rather than generating duplicate measurements.

Training IDs and held-out IDs are disjoint within each split. Retain the selected
IDs, logical trace, batch maps, all three calibration costs, selected order,
source/config hashes and original-query accounting. The new policy was motivated
by already inspected test outcomes, and queries recur across splits; this is an
exploratory evaluation, not an untouched confirmatory test. Do not tune the
50-query budget, choose a policy per test query, discard regressions, or select
using held-out timings.

## Comparisons and limits

Report the selected path against each fixed order under identical BFS placement,
batching and memory settings, with ten-split paired intervals. Show selection
counts and difference from the retrospectively best fixed order in each held-out
split. That best-order comparator is a descriptive oracle, not a deployable
method. Report calibration service cost separately; no CPU/PIM wall-clock or
application break-even claim follows from these trace timings.

At the default configuration, also compare with published RCM/Gorder/Porder under
original-order bounded replay, using the already retained matching evidence.
Those are comparisons of measured configurations; published placements combined
with this selector remain untested. Full PIM systems from the literature differ
in hardware, compute and workload, so no numerical accelerator-speedup comparison
will be invented from their headline results.

The expected contribution is an evidence-backed engineering recommendation:
profile the vector-fetch schedule at the execution boundary where the target
exposes parallel requests, while preserving HNSW's search semantics. Profiling
and choosing among established orders is not claimed as algorithmic novelty.
