# Compact access plans: exploratory follow-up

Started 23 November 2026 before execution of the new kernels. Preserve the
earlier WRAM pilot unchanged. This experiment investigates a candidate, not an
established novel contribution or a guaranteed improvement.

## Hypothesis

For repeated indexed aggregation with fixed connectivity, preparing WRAM slot
and load decisions once on the host can reduce DPU bookkeeping enough to make
retention useful. A plan replaces each 32-bit source index with one 32-bit
instruction: load flag, source index on misses, and WRAM byte offset. It keeps
input ordering, output arithmetic and index-stream size unchanged.

This is an inspector/executor approach. Offline caching, scratchpad allocation,
and Belady replacement are established techniques. The candidate contribution
would have to concern the UPMEM encoding, measured instruction/traffic trade-off,
and amortization boundary. Absence from a few papers is not novelty proof.

## Comparisons

- Streaming with 128- and 256-byte index buffering.
- Runtime direct-mapped history caching.
- An encoded plan with the **same direct-mapped decisions**, isolating lookup
  overhead from replacement quality.
- An encoded next-use plan using known input order (offline Belady replacement).
  Its full input knowledge is available only for exposed/repeated worklists.
- Planned LRU replacement as a simpler offline-planning control.

Use a common row-oriented reduction kernel for all policies. Retention receives
512 bytes/tasklet; all methods fit the same 64 KiB WRAM ceiling including the
upstream linker's reserved stacks. Start with four tasklets, then test twelve
tasklets before any recommendation. Keep all baselines and negative cases.

## Accounting and checks

Validate every output feature, exact MRAM read/write bytes and plan semantics.
For the direct-map pair, require identical feature-load counts. Count plan
storage and construction time. A plan replaces indices rather than adding a
second DPU stream. Fresh feature values must be loaded on each execution;
topology, processing order, tasklet partition or resource changes invalidate it.

Report complete DPU kernel cycles; separately derive the number of repeated
executions needed to amortize host planning. Host transfer/launch times are not
measured by this model and must remain explicit unknowns. Integer aggregation
does not demonstrate floating-point ML performance. Energy and GPU results
are outside this experiment.

Initial screening uses seed 7; held-out generated inputs use 23 and 61 only
after the implementation/selection rule is fixed. These are exploratory tests,
not a large confirmatory campaign. Include a small real graph-derived workload
if acquisition is straightforward. A sub-5% simulated benefit is mechanism
evidence, not a hardware deployment recommendation. No extra MRAM traffic is
the primary acceptance limit. No arbitrary tuning on held-out results.

## Screening update (before seeds 23/61)

The initial 18 records at 64 bytes/four tasklets show no plan beating streaming.
The direct-map plan removes instructions and is faster than runtime caching,
but this is insufficient. Retain these records and their original sources.
Next test 8-byte graph-state records and 256-byte feature rows at twelve
tasklets, and a 16-bit streaming-index baseline where source IDs fit. Against
that compressed baseline the 32-bit plan adds index bytes; count this explicitly.
The proposed traffic guarantee applies only against an equal-width 32-bit
stream unless additional feature-read savings cover the larger index stream.

## Batch variant and held-out check

The 63-record footprint screen also finds no per-access plan faster than
streaming. A three-case follow-up replaces per-reference load flags with
64-reference batches: fetch the batch's unique 8-byte records once, then
consume byte-sized WRAM slot indices. Headers, dictionaries, alignment padding
and tasklet-segment storage padding are charged. The three seed-7 screens do
not beat 16-bit streaming; community access comes closest.

Freeze this batch implementation and check seeds 23 and 61 on community,
uniform, hub-heavy and sampled ca-GrQc neighborhoods. Use twelve tasklets and
8-byte records, and retain 32-/16-bit streaming, runtime caching and next-use
plans as controls. This is a bounded generalization check, not another tuning
round. The real workload samples eight neighbors with replacement for each of
192 randomly selected ca-GrQc vertices; it is not a full graph pass. Source:
https://snap.stanford.edu/data/ca-GrQc.html, compressed file SHA-256
`a254442cdf5d684712578b630c2e0d7543518ab154ef2341cabb607572ce7230`.

If the candidate still fails, do not describe it as a successful new method.
Quantify its failure and distinguish the known compression improvement from
an original research contribution. PIM–GPU integration remains conditional.
