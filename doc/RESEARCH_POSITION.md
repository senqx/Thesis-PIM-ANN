# Research position and Master's scope

The central question is: **when the search needs the same vectors, which tested
placements and request schedules make the specified memory system finish sooner?**
The thesis is an engineering study motivated by PIM. It measures memory service
with a simulator and checks which execution assumptions determine the result.

## What is already established

| Prior work | Public status checked on 10 November 2026 | Consequence for this thesis |
| --- | --- | --- |
| HNSW | Published in IEEE TPAMI, 2020 | The search algorithm is a baseline, not a new contribution. |
| Coleman et al., graph reordering for cache-efficient near-neighbour search | Published at NeurIPS 2022 | Graph placement, including profile-guided **Porder**, already exists. The 2021 preprint omits that later extension. |
| DRIM-ANN and UpANNS | Published at SC 2025 | ANN on commercial or enhanced PIM, including compute and data-movement co-design, is established research. |
| PIMANN | Published at USENIX ATC 2025 | Fine-grained PIM scheduling is established; request sorting here is a different, narrower intervention. |
| PIMCQG | Its 3 November 2026 public revision states **accepted at SC26** | Graph ANN/PIM co-design is already covered by directly relevant systems work. |

Links and exact titles are in the [shared bibliography](references.tex). This is
a targeted public-literature comparison; it cannot inventory unpublished work.

Neither query-guided placement nor the row-reuse/bank-parallelism trade-off should
be claimed as an invention. The contribution is the measured interaction of
placement, request availability, footprint and controller service in the checked
artifact. Published placement routines provide stronger comparisons than the
local heuristic alone. Their application benchmarks include effects, particularly
caches and native index allocation, that this DRAM study does not reproduce.

The concrete original outputs are the checked comparison at fixed HNSW search
work; the measured placement and scheduling reversals under explicit request
availability, footprint and controller settings; and the exploratory evaluation
of a training-selected order against fixed schedules and published placements.
The accompanying execution sketch explains how to test those findings in a
system. None of these claims requires ownership of graph reordering, profiling,
round-robin scheduling or the idea of accelerating ANN near memory.

The DRAM mechanism can affect host systems too. The specific PIM implication is
to evaluate a configurable gather-and-distance interface: host control discovers
candidates and supplies addresses, while an engine consumes resident vectors and
returns tagged distances. Gathering alone still sends the vector payload to host
arithmetic. Local distance evaluation could avoid that transfer, but requires
arithmetic, query storage, buffering and a compatible request interface. The
thesis's [execution section](execution_sketch.tex) specifies this division and its
unmeasured costs. This is architectural guidance, not measured PIM acceleration.

## The research questions

1. **Mechanism:** how do order, contiguous runs and concurrency affect completed
   service, and when do locality statistics disagree with timing?
2. **Central workload question:** which tested placements and schedules help on
   held-out SIFT queries at fixed logical search work, and can a short training
   profile select a useful schedule?
3. **Robustness:** do those conclusions survive selected changes in available
   requests, footprint, controller settings and graph construction?

These questions belong to one argument. The microbenchmarks explain a mechanism;
the real HNSW traces test whether it matters; the follow-up tests established
baselines and ordering within an available expansion. Controller and graph
variations support interpretation. They are not separate proposed theses.

## What counts as a useful result

A negative result should identify the method, baseline, workload and assumptions
under which it fails. A loss by one greedy heuristic does not prove that training
is useless. A loss by address sorting does not prove that all scheduling is
useless. Conversely, a positive simulation result identifies a service-time
opportunity before overhead; it is not automatically a working PIM accelerator.

The current evidence retains both the original flat replay and the expansion-
bounded extension. The latter limits future memory work but still omits distance
computation, caches/local storage, mapping traffic and scheduling cost. Its
candidate-vector overlap is an explicit assumption. The per-query service check
also examines whether an average saving hides regressions; those query records
are not treated as additional independent experimental replications.

## Where to stop, and what would justify more work

The proposed execution extension stays inside the central question. It selects
original, sorted or round-robin vector fetch using 50 training queries for each
configuration, then freezes that choice for held-out service. The sensitivity
matrix shows why footprint alone cannot select an order: outstanding capacity
and address mapping can reverse its effect. The proposal is a configuration-aware
gather path for hardware that exposes the required requests. It is not an
algorithmic novelty claim or an assumed interface of commercial UPMEM.

The [fixed design](PROFILED_FETCH_DESIGN.md) records the policy, comparisons and
exploratory status. It was motivated by previously inspected test outcomes.
Training and test queries are disjoint within each split, but that separation
does not turn the research process into untouched confirmation. The complete
held-out results, selection counts, oracle gaps and profiling costs are presented
in the thesis; published placements combined with this selector remain untested.

A defensible Master's conclusion can be conditional on one real corpus prefix,
a specified HNSW operating point and a specified simulator. Here that point is
128-dimensional SIFT, `M=16`, construction width 200, search width 64 and `k=10`.
The additional construction seeds test limited graph variation, not different
datasets, dimensions, graph families or recall targets. The 128-byte repacking
changes transfer size while keeping float32 search. Ten paired splits estimate
query-selection variability conditional on those choices; they do not establish
generality or a universal sample-size requirement. The thesis must complete the
checks needed for these comparisons, without claiming a universal winning layout.

If the intended claim becomes **practical PIM application acceleration**, the next
necessary experiment is an execution path that charges the proposed schedule for
candidate discovery, distance computation, local buffering, mapping and
communication. If the intended claim becomes **broad ANN generality**, new datasets
and search operating points become necessary. Neither stronger claim follows
from adding more repeats of the same current trace.

The current work can support a focused empirical paper. Publication novelty and
venue fit still require comparison with that venue's expectations; a clean
simulation result alone is not a guarantee of acceptance.

## Earlier work remains available

The [preservation guide](RESULTS_PRESERVATION.md) distinguishes the validated
checkpoints from material superseded by correctness repairs. All 1,289 earlier
validated replays remain in their original paths. A tighter main narrative does
not discard them or turn them into invalid evidence.
