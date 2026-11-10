# Research position and Master's scope

The central question is: **when the search needs the same vectors, which tested
placements and request schedules make the specified memory system finish sooner?**
The thesis is an engineering study motivated by PIM. It measures memory service
with a simulator and checks which execution assumptions determine the result.

## What is already established

| Prior work | Public status checked on 10 November 2026 | Consequence for this thesis |
| --- | --- | --- |
| HNSW | Published in IEEE TPAMI, 2020 | The search algorithm is a baseline, not a new contribution. |
| Gorder | Published at SIGMOD 2016 | Structural graph ordering is established; this artifact uses the routine supplied with Coleman et al.'s comparison. |
| Coleman et al., graph reordering for cache-efficient near-neighbour search | Published at NeurIPS 2022 | Graph placement, including profile-guided **Porder**, already exists. The 2021 preprint omits that later extension. |
| DRIM-ANN and UpANNS | Published at SC 2025 | ANN on commercial or enhanced PIM, including compute and data-movement co-design, is established research. |
| PIMANN | Published at USENIX ATC 2025 | Fine-grained PIM scheduling is established; request sorting here is a different, narrower intervention. |
| PIMCQG | Its 3 November 2026 public revision states **accepted at SC26** | Graph ANN/PIM co-design is already covered by directly relevant systems work. |

Links and exact titles are in the [shared bibliography](references.tex). This is
a targeted public-literature comparison; it cannot inventory unpublished work.

## The original contribution

**This thesis quantifies when established placement and fetch-order choices help
or fail for a fixed HNSW/HBM2 workload, explains observed reversals with DRAM
command evidence, and derives constraints for a compatible near-memory
implementation.** The contribution is empirical: the measured cases, their
explanation and the resulting design guidance. The general locality–parallelism
trade-off, graph reordering, PIM-based ANN, locality optimisation and fine-grained
scheduling are established ideas.

The three contributions in the thesis introduction have the following evidence
and intended use. All percentages below are mean paired changes across ten query
splits in **simulated completed DRAM service cycles**; negative means fewer cycles.
Both footprints retain the same float32 search; 128 bytes is hypothetical repacking.

| Contribution | Concrete evidence produced here | What it helps an engineer decide |
| --- | --- | --- |
| **C1. Measured limits of locality-oriented placement** | The local query-aware placement changes default flat-replay cycles versus BFS by −0.31% at 512 bytes and +0.17% at 128 bytes, despite more row hits at 128 bytes. RCM/Gorder/Porder comparisons show that the local heuristic does not exhaust placement opportunities. | Whether a locality improvement actually reduces service time, and whether an established placement is a stronger baseline than the proposed heuristic. |
| **C2. Conditional scheduling gains and explained reversals** | Expansion-bounded BFS round-robin changes cycles versus matching original order by −14.58% at 512 bytes and +3.43% at 128 bytes. Changing only the mapper makes the 512-byte effect +112.71%. On reference split one, the default 512-byte schedule adds 277,894 command cycles but removes 1,429,356 no-command cycles. | Whether the proposed fetch interface exposes useful parallelism, and which mapping, availability and request-limit assumptions must be checked before choosing an order. |
| **C3. An exploratory execution recommendation with explicit cost thresholds** | A 50-query profile selects among three existing orders. The default 512-byte service gain is about 5,802 cycles/query; extra cost reaching that value erases the gain in a serial additive model. The selected BFS path beats original-order Porder by 14.25% there, but loses to original-order Gorder by 1.35% at 128 bytes. | Whether a fixed or profiled order merits implementation testing, and how much incremental scheduling, buffering and transfer cost the service saving could tolerate. |

C1 and C2 are the core empirical findings. C3 is supporting engineering guidance
derived from those findings using established selection and cost models; neither
profiling nor the amortisation formula is claimed as an invention.

The [placement comparisons](generated/followup_layout_table.tex),
[scheduling matrix](generated/scheduling_table.tex),
[command accounting](generated/followup_mechanism_table.tex) and
[profiled comparisons](generated/profiled_fetch_baselines.tex) give the detailed
evidence, including paired intervals where applicable. The
[reproduction guide](REPRODUCIBILITY.md) connects the generated results to raw
records, fixed protocols and runnable commands.

### Exactly how this differs from the named systems

**Compared with Gorder and Porder**, the added result is a controlled evaluation
of their supplied placement routines at the DRAM-service layer, with logical
search work fixed and request availability explicit. It does not introduce those
ordering methods or reproduce their application benchmarks. Cache hits can avoid
DRAM requests entirely, whereas row hits still require DRAM service. Consequently,
their cache-aware application gains and these service differences answer
different questions; a small effect here does not refute their results.

**Compared with DRIM-ANN, UpANNS, PIMANN and PIMCQG**, the added result is a set of
isolated fetch-path comparisons and implementation constraints within the larger
ANN/PIM design problem. Those systems contribute architectures and execution
techniques involving computation, storage and communication. This thesis measures
neither those systems nor a replacement accelerator. Its percentages therefore
cannot rank it against their reported application speedups. In particular,
PIMANN already establishes fine-grained PIM scheduling, and PIMCQG directly
addresses graph ANN on PIM. The question here is how a compatible engine should
order the reads for already-discovered candidate vectors, under stated DRAM
and availability assumptions.

The targeted literature comparison supports this distinction in contribution
and measurement scope. It is not proof that every aspect of the interaction is
absent from all prior work, or that this is the first study of the general idea.

### What the work gives other researchers and engineers

The artifact supplies **reproducible failure cases, conditional alternatives and
cost thresholds**. A researcher can use its fixed-search pipeline to compare a
placement without confounding the result with changed traversal or recall. A
memory-system engineer can reproduce the gain and regression of a candidate
schedule under explicit request boundaries. An accelerator designer can use the
measured saving as a budget to test against implementation costs, keeping a
simple fixed schedule when profiling adds no value.

These uses are concrete even though deployment gains remain unmeasured. The
negative results rule out particular recommendations under the tested conditions;
they do not prove that locality or scheduling is generally ineffective. The
positive results identify where implementation testing is justified; they do not
promise a working speedup on another workload or memory platform.

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
validated replays remain in their original paths. The current matrix adds 360
scheduling and 420 calibration records, for **2,069** in total; the
[campaign inventory](REPRODUCIBILITY.md#record-counts-and-frozen-protocols) explains
why frozen protocols still cite the earlier count. A tighter main narrative does
not discard earlier work or turn it into invalid evidence.
