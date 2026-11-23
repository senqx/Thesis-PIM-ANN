# Prepared access decisions: experimental development

For the current concise narrative, read the [short thesis](../thesis/short-thesis.md).
The [five-point extension](../experiments/access-plan-fivepoint/README.md)
preserves the results below, adds two intermediate sizes and uses a separate
new preparation campaign. Its timing estimates are the ones used in the thesis.
The later [baseline controls](../experiments/baseline-gates/README.md) improve
dictionary encoding and establish shared residency as the strongest tested
choice for the small feature tables. This note preserves the earlier mechanism
and results; use the [contribution plan](CONTRIBUTION_PLAN.md) for the active RQs.

Focused follow-ups, 23 November 2026. **The initial small-workload candidate
lost; larger repeated workloads reveal a conditional simulated benefit.**
See the [preparation/work-size study](../experiments/access-plan-scaling/README.md)
for the updated boundary. This is not a verified novelty claim. The
preceding [WRAM pilot](../experiments/wram/README.md)
showed that fewer transfers can lose to the instructions used to manage them.

## The idea in ordinary terms

If the same graph connectivity is processed repeatedly, the sequence of
neighbor IDs is already known. Instead of making the DPU repeatedly ask
“is this row cached, and which row should I evict?”, the CPU can prepare those
decisions once. The DPU follows a compact list telling it which WRAM slot to
use and when to load a fresh value into that slot.

```text
Graph/index order + tasklet allocation + feature width + WRAM allowance
                              ↓
                   CPU builds an access plan
                              ↓
       DPU reads a plan word → loads if instructed → aggregates
                              ↓
          Reuse the plan with new feature values on the next pass
```

Only the access decisions persist. Each execution starts with logically empty
WRAM and loads current feature values from MRAM. This avoids reusing stale
features when values change between layers or iterations. Rebuilding is needed
when topology, order, partition, feature width or the WRAM allocation changes.
Concurrent feature updates during a pass are unsupported.

The prototype replaces each 32-bit source index with a 32-bit plan word:
one load flag, a source ID for loads, and a WRAM byte offset. It retains the
original mathematical operation order and fetches no unrequested feature rows.
Against a 32-bit index stream, plan traffic equals index traffic and feature
traffic cannot exceed demand fetching. This guarantee does **not** automatically
hold against a 16-bit index stream; that is an explicit baseline in the tests.

The intended scope is repeated, exposed index sequences: fixed-topology graph
propagation or aggregation, or repeated sparse operations. This is not a
prefetcher that predicts unseen HNSW candidates or changing BFS frontiers.
There is no assumed asynchronous DMA primitive. Data movement is scheduled
explicitly, and each issuing tasklet still blocks for its own DMA.

## What is already known, and what would need to be our contribution?

| Prior work | What is established | Boundary relevant to this candidate |
| --- | --- | --- |
| [SparseP](https://people.inf.ethz.ch/omutlu/pub/SparseP-SpMV-in-Real-Processing-in-Memory-Systems_pomacs22-arxiv22.pdf), §3.5 | Coarse streaming of sparse metadata and fine indirect reads; blocked formats and multiple balancing strategies. | A necessary strong baseline. Our prototype is not an implementation or performance reproduction of the full SparseP library. |
| [PyGim](https://arxiv.org/pdf/2402.16731v7), §3.2 kernel implementation | Chunked adjacency reads, row-granularity feature reads, WRAM output accumulation, and tuning across DPU clusters. | The inspected kernel discussion does not describe a per-edge encoded residency plan. It already establishes efficient GNN/PIM decomposition. |
| [ATiM](https://arxiv.org/pdf/2412.19630v3), §§5–7 | Automatically chooses WRAM tiles, schedules transfers and optimizes generated instructions. | Compiling memory management and tuning capacity are not new. The candidate concerns an exposed irregular index sequence and per-reference residency decisions. |
| [ALPHA-PIM](https://arxiv.org/pdf/2602.09174), §§4.2 and 7 | Selects sparse/dense graph-processing variants using input sparsity and discusses pipeline, scratchpad and synchronization costs. | Workload-dependent selection on UPMEM is already established; an adaptive selector alone is not our novelty. |
| [UPMEM Unleashed](https://arxiv.org/pdf/2510.15927v1), §§III and VI | Finds compiler/runtime inefficiencies; improves arithmetic kernels, unrolling, data access, and host communication. | Reducing instruction overhead or optimizing integer arithmetic is already published. Its results also emphasize amortizing placement through data reuse. |
| [PRISM](https://arxiv.org/pdf/2605.29728), §IV | Sparse tensor formats, hierarchical partitioning, fixed-point arithmetic and CPU/PIM work distribution. | A different sparse workload with substantial partitioning/data-reuse prior art; “new sparse data placement” would be too broad a claim. |

Inspector/executor separation, partial evaluation, offline cache replacement
and scratchpad allocation are older than these UPMEM papers. For example,
[FreeTensor](https://doi.org/10.1145/3519939.3523448) addresses irregular tensor
programs with partial evaluation and dependence-aware transformations on
CPU/GPU; its abstract was inspected, not its complete implementation. The
next-use policy here uses **Belady's established replacement rule**; it is not
a newly invented predictor.

The possible contribution is therefore narrower: **an inexpensive UPMEM access
representation plus a measured decision boundary showing when it repays its
instruction, planning and storage costs under a fixed traffic budget**. That
could be a useful Master's contribution if demonstrated beyond weak baselines.
The current review found no exact match in the inspected mechanisms; it cannot
prove that no compiler or scratchpad paper implements an equivalent scheme.

## What the bounded experiment established

The [execution study](../experiments/access-plan/README.md) contains 132
performance configurations. Per-reference plans lose to streaming at 8-, 64-
and 256-byte feature widths in the screened settings. The same-load control
does remove lookup instructions; that saving does not make retention win.

A subsequent batch variant moves all load decisions before a 64-reference
aggregation loop. On fresh seeds with twelve tasklets and 8-byte features,
it reduces MRAM reads by 48.41% on community inputs and 41.64% on sampled
ca-GrQc neighborhoods, but increases cycles by 0.25% and 4.91%, respectively.
Uniform inputs increase both cycles (52.77%) and read traffic (25.73%). These
are two-seed descriptive means against **16-bit-index streaming**. Compressed
indices are a necessary control: they improve cycles by 5.75–6.03% over the
best tested 32-bit streaming variant across the held-out family means.

Two separate checks change feature values while reusing identical access
metadata and linked programs. Both batch and next-use plans produce the new
reference sums. Thus the intended plan lifetime is functionally supported,
but that initial small-workload study has no positive per-execution saving to
amortize against the strongest baseline.

This narrows the opportunity: **reuse must be exposed in a representation
whose instruction and metadata costs are smaller than the transfers it
avoids**. Better eviction decisions alone do not establish that condition.
The near-tie motivated the bounded size follow-up below. It does not by itself
justify an adaptive framework or a hardware speedup claim. Generic batch dictionaries, offline
planning and index compression already have substantial prior art.

## Preparation, amount of work and valid reuse

The follow-up separates total work, batch window and plan lifetime. At 3,072
destinations, batch64 reduces cycles by a two-seed mean of 5.35% on community
inputs and 5.05% on sampled ca-GrQc neighborhoods, against the fastest of
three compressed-index streaming buffers. Smaller jobs and uniform access
remain important failures. The larger workload is the best tested size, not
a proved global optimum.

The reference Python planner costs about 7.03 ms for the larger community
worklist, versus 0.35 ms for streaming-index encoding. The kernel saves about
79 µs per invocation. Preparation therefore needs 83–86 valid uses to be
repaid, before differential installation; the sampled graph needs 69–94.
The [full accounting](../experiments/access-plan-scaling/README.md) includes
plan storage, assumed installation rates, per-seed thresholds and all failures.
Preparation grows approximately with work in the measured range, so simply
increasing work cannot make its cost disappear.

Local reads fall by about 48% and 41%, respectively, but installed metadata
grow by about 27–29% and 40–42% relative to compressed indices. This fails a
strict zero-extra-host-setup budget despite the local traffic benefit. It
supports a narrower, reusable-plan opportunity under disclosed setup costs;
hardware timing, optimized host preprocessing and broader input coverage
remain unresolved. No trained adaptive selector or GPU experiment is implied.

## Evidence required for a successful continuation

1. Compare a runtime direct-mapped cache with a plan that makes exactly the
   same loads. This isolates removing lookup instructions from better caching.
2. Compare streaming, compressed indices, simple offline LRU and next-use
   replacement. Keep poor-reuse workloads, larger features and full tasklet
   occupancy in the evaluation.
3. Include planning, extra host state and plan installation in amortization.
   A lower DPU time is insufficient when the graph is used only once.
4. Preserve the feature-update correctness check when extending plan lifetime
   across real layers or iterations, including invalidation when access order
   or ownership changes.
5. Check a real graph-derived input and obtain hardware timing validation
   before making an application or deployment claim.

If a plan saves ΔT seconds per DPU execution, its break-even reuse count is
approximately `ceil((planning + extra installation) / ΔT)`, provided ΔT is
positive. This is a serial kernel-only accounting model, not a prediction of
CPU/GPU pipeline throughput. Multi-DPU planning, host contention and overlap
need separate measurements. Our Python planner includes validation and is a
reference implementation; its measured cost is not a lower bound for optimized
C/C++ preprocessing.

The [experiment protocol](../experiments/access-plan/PROTOCOL.md) and associated
records retain both successes and failures. No PIM–GPU experiment has been run.
If a local policy succeeds, the next CPU-coordinated extension must compare
equivalent CPU gather/reduce and GPU-resident baselines, with dispatch, staging,
merge and GPU time included as described in [PIM–GPU feasibility](PIM_GPU.md).
