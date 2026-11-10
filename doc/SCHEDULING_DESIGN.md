# Scheduling robustness: fixed design

Recorded on 10 November 2026 before inspecting these timings. This supplements
the 1,289 validated replays at `94d3f1d`; that checkpoint remains unchanged.

The question is whether the observed scheduling contrast survives selected
changes in request concurrency, candidate batching and address mapping. Earlier
controller sweeps concern flat placement and cannot answer this new question.

## Matrix and stopping rule

Use BFS placement on the reference graph, all ten existing query splits, and
both 512-byte float32 and hypothetical 128-byte footprints. Compare original
order, address sorting and transaction round-robin in every condition:

| Condition | Intervention relative to the previous bounded model |
| --- | --- |
| Outstanding 16 | At most 16 uncompleted native transactions |
| Outstanding 32 | At most 32 uncompleted native transactions |
| Outstanding 128 | At most 128 uncompleted native transactions |
| Candidate batch 2 | Split each vector phase into consecutive groups of at most two vectors; drain each group |
| Candidate batch 8 | As above, with groups of at most eight vectors |
| Alternate mapping | Use the already evaluated `ChRaBaRoCo` mapper |

These are separate interventions, not a factorial sweep. Unchanged settings are
64 outstanding transactions, a 32-entry controller read buffer, one issue
opportunity per controller cycle, readiness-first FRFCFS, open pages and the
pinned HBM2 model. The 128-outstanding case does not enlarge the read buffer.
The existing default results are reused, not relabelled as new measurements.

The matrix adds **360 replays**: six conditions × three schedules × two
footprints × ten splits. Complete this matrix and retain every outcome. Do not
add samples or methods merely to obtain a preferred sign. A one-vector batch is
an exact-order sanity test: all three schedules must emit the same stream. It
does not need three additional timing campaigns.

The queries have been used before. These are paired exploratory sensitivity
comparisons conditional on one graph and corpus, not independent confirmation
or a cross-dataset generalisation test. Report ten-split paired differences and
95% Student intervals, absolute saved cycles, and descriptive query/p95 effects.
The existing alternate graph constructions remain supporting evidence for the
default scheduling configuration; they are not repetitions of these new axes.

## Meaning of a candidate batch

Batching inserts memory-completion boundaries inside an existing vector phase.
It preserves the original candidate order before applying a schedule within each
batch, and preserves every request and its original query/expansion membership.
A batch drains fully before the next one starts. This is a conservative batch
execution model, not a rolling limit on resident vectors or an instruction-level
PIM simulation. A fair scheduling comparison uses identical batch boundaries.

Distance arithmetic, visited-set/queue work, candidate-address construction,
buffering cost, caches/local storage, mapping traffic and host/PIM communication
remain omitted. Inter-query overlap remains unevaluated. Timing differences
between batch sizes include the newly imposed drains; they are not arithmetic
cost measurements or universal execution bounds.

## Required evidence

* Verify the reused graph, logical records, BFS mappings, splits and returned IDs
  against the previous checkpoint before emitting requests.
* Independently reproduce the existing flat BFS trace hashes at both widths.
* Reconstruct batch membership from the preserved phase map; each original phase
  is covered exactly once, without mixing queries or adjacency/vector phases.
* Preserve each batch's transaction multiset across all three schedules and
  retain its phase map, trace hashes and losslessly compressed service intervals.
* Validate the complete named matrix, simulator/config identity, every read count
  and aggregation back to original-query service including inter-batch gaps.
* Keep the source/binary behind earlier measurements unchanged. New code and
  evidence have their own hashes and paths.

No new placement algorithm or layout/schedule combination is part of this pass.
The existing BFS/round-robin versus Porder/original comparison is an additional
summary of already measured configurations, explicitly distinct from an untested
Porder/round-robin combination.
