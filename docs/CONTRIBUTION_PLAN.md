# When is WRAM reuse worth it?

24 November 2026. **Planning record, followed by a completed evaluation.** The
[standard-workload study](../experiments/decision-study/README.md) implements
SpMV/SpMM, stronger baselines, native costs and a frozen held-out selector.
The selector fails its practical-success criterion; the results support scoped
static-retention guidance and a negative result for this model. The prospective
text below preserves the plan rather than retroactively rewriting its hypothesis.
The [thesis draft](../thesis/short-thesis.md)
distinguishes the retained 23 November experiments from the completed continuation;
the [validation record](VALIDATION.md) dates the evidence and document checks.
This plan updates the research direction: choosing among established
approaches is the core contribution to investigate. A new selective preparation
algorithm is optional, rather than a required outcome.

The [24 November novelty audit](NOVELTY_AUDIT.md) checks this objective against
published methods and selected official implementations. It finds substantial
overlap. The follow-up supplies empirical comparisons, not an established novel
algorithm or a successful general selection rule.

The completed thesis is **Stage 1: an experimental investigation of the costs
and benefits of local data reuse on UPMEM**. Its selector chooses how to serve
known accesses. **Stage 2**, predicting future requirements from topology and
traversal state, is possible next research. **Stage 3**, coordinating placement,
work assignment and transfers across heterogeneous resources, is a longer-term
direction. Neither later stage is claimed as a completed contribution or a
required extension of this paper. The failed-selector result remains a central
Stage 1 finding. Section 14 of the thesis separates these stages explicitly.

## The engineering question

An engineer has assigned work to a UPMEM DPU. Should the program stream data
from its large local memory (MRAM), keep selected data in its small working
memory (WRAM), or prepare batches that reuse values? **When does each approach
save more execution time than it costs, and under which resource limits?**

The objective is to develop and test a small, understandable decision model
for this choice on standard indexed-access kernels. Its inputs should describe
the workload and available resources, rather than identify a benchmark by name.
The output should be a recommendation, its estimated cost, and the conditions
under which the recommendation has been validated.

This is a decision *within* a DPU. Deciding whether a complete application
should run on UPMEM, a CPU or a GPU requires system-level implementations and
measurements beyond the available platform. Local traffic savings do not
establish application speedup or energy savings.

## Three connected research questions

### RQ1 — Which scenarios favor each approach?

**How do working-set size, access reuse and record width change the relative
cost of streaming, WRAM retention and prepared batches?**

Use standard kernels to identify conditions in which each feasible approach
wins or loses. Explain the result using complete kernel cycles, transferred
bytes, metadata and WRAM use. Saved reads alone are not an explanation: lookup
instructions, synchronization and available tasklet concurrency also matter.

### RQ2 — When is the saving worth the preparation?

**How much valid work is needed to repay inspection, preparation and
installation, under the same WRAM capacity and explicit traffic and storage
budgets?**

Measure setup costs for every compared approach, including unsuccessful
inspection. Distinguish a long worklist from repeated execution of one worklist.
Report when payback is impossible, when it is conditional, and how updates
invalidate a prepared plan or require retained values to be reloaded.

### RQ3 — Can those findings guide a new input?

**Can a simple model choose a useful approach on held-out inputs more reliably
than a reuse-only rule or one calibration-selected fixed approach?**

Freeze the model before evaluating complete held-out datasets and request
streams. Report wrong choices and their cost, as well as successful choices.
If a simple fixed approach is just as effective, that is a useful answer.
A complex adaptive mechanism is justified only by a remaining measured need.

The path is **characterize the scenarios → account for all costs → test a
practical recommendation**. The intended research output is evidence about
where the choices change, and a validated way to use that evidence. A catalogue
of benchmark timings alone would not answer RQ3.

## Standard tasks with a reason for each one

| Task | Familiar use and operation | What it adds to the investigation | Starting point |
| --- | --- | --- | --- |
| Sparse matrix–vector multiplication (SpMV) | Compute `y = A x`; each sparse matrix row gathers selected entries of `x`. Used in sparse solvers and graph calculations. | Narrow records, inexpensive arithmetic and irregular source reuse. | [SparseP](https://github.com/CMU-SAFARI/SparseP); public matrices from the [SuiteSparse collection](https://sparse.tamu.edu/). |
| Sparse matrix–dense matrix multiplication (SpMM) | Compute `Y = A X`; each selected source contributes a vector. This includes the aggregation step of many GNNs. | Vary feature width on the same sparse structure to test transfer granularity and WRAM pressure. | [PyGim](https://github.com/CMU-SAFARI/PyGim); public sparse matrices or graphs with a declared weighted or unweighted operator. |
| Embedding lookup and summation | Gather vectors for a list of IDs and sum them, as in recommender models. | Test a separate request source, especially whether popular IDs remain popular across successive batches. | [UpDLRM](https://arxiv.org/abs/2406.13941); select and pin a publicly redistributable request source before making application claims. |
| Sequential vector addition, as a small control | Read contiguous arrays and add corresponding values. | Check a regular stream with no indirect source reuse; expose preparation overhead when there is little to exploit. | [PrIM](https://github.com/CMU-SAFARI/prim-benchmarks). |

These are established algorithms. SpMV, SpMM and GNN aggregation share sparse
operations; their names do not make them independent proof of generality.
Embedding summation also shares a gather-and-reduce structure. The proposed
scope is therefore **regular and indexed access with an exposed worklist**,
not all irregular computation. Dependent pointer traversal, changing BFS
frontiers and distributed graph updates remain outside it.

Use the published implementations as references and, where compatible,
baselines. Record any port, simplification or omitted feature. A custom kernel
inspired by SparseP is not a reproduction of SparseP. Use native public input
structures for the application checks; synthetic inputs isolate individual
causes but cannot replace them. The existing sampled, fixed-degree aggregation
is retained as pilot evidence, not relabelled as a complete standard benchmark.

Start with SpMV and SpMM because they share infrastructure. Add embedding
summation only after confirming that its inputs expose a distinct access or
plan-lifetime scenario at modest implementation cost. Full neural-network
training and dense GPU layers are application context, not promised workloads.

## A testable hypothesis

**For a fixed UPMEM configuration, observable working-set size, reuse, record
width and valid plan lifetime can guide a choice among established local-memory
approaches that lowers total accounted time on held-out indexed-access inputs,
compared with choosing one fixed approach on calibration data, while satisfying
the same declared capacity and byte budgets.**

The experiment may reject this hypothesis. Before final evaluation, declare
what improvement would be practically useful and how model uncertainty will
be handled. Failure includes savings erased by setup, frequent costly wrong
choices, or a fixed baseline performing equally well. Neither saved bytes nor
a statistically detectable but negligible saving is sufficient by itself.

## What “worth it” includes

For an approach `s` and `K` valid uses of a worklist, use the initial serial
accounting model:

```text
T_s(K) = P_s + I_s + sum(E_s,k + U_s,k, for k = 1..K)
```

- `P_s`: inspection, profiling and construction, including a rejected plan.
- `I_s`: initial installation of its representation and any extra data.
- `E_s,k`: complete DPU execution, including local transfers, lookups,
  initialization, barriers and output writes on use `k`.
- `U_s,k`: additional host transfers and refresh work needed for that use.

Common costs may cancel only after checking that their work and byte volumes
are identical. Count an initial preload inside kernel execution or installation
as appropriate, once. Report cold and repeated execution separately. A stable
index plan does not mean feature values stay unchanged; current kernels reload
values on every invocation.

If per-use costs are stable, let `Delta P`, `Delta I` and `Delta R` be candidate
minus streaming setup, installation and per-use time. Then the candidate is
faster only when:

```text
Delta P + Delta I + K * Delta R < 0
```

With positive extra setup and a positive per-use saving `S = -Delta R`, the
condition is `K > (Delta P + Delta I) / S`. If the candidate saves no time per
use, repeated execution cannot repay positive extra setup. Near-zero savings
make the threshold fragile; report a sensitivity range instead of a universal
reuse count. Preparation and plan lifetime are established concepts, not a
novel formula claimed by this thesis.

Measure comparable native host preparation for practical recommendations.
Current Python preparation timings remain valid reference measurements for
the original implementation only. Without hardware, installation and refresh
times require clearly stated transfer assumptions; mark totals that combine
measured and simulated components as modelled. A serial sum does not establish
pipeline throughput or justify assuming communication/computation overlap.

All methods have the same total WRAM ceiling and comparable tuning opportunity.
Use linked allocations, including stacks, indices, output buffers and alignment.
The current linker reserves 49,152 bytes of a 64 KiB WRAM for stacks; the nominal
capacity is not the capacity available for retaining source values.

The primary constrained comparison allows no growth in installed index/plan
bytes or local MRAM–WRAM transferred bytes relative to matched streaming.
Report reads and writes separately and apply limits per input, not on averages.
Also show the unconstrained trade-off when a faster approach exceeds a budget;
it does not qualify as a win under the primary constraint. Report host temporary
storage and all host–DPU bytes so costs cannot be hidden at another boundary.
Transferred bytes are a traffic budget, not a measurement of bandwidth or energy.

## Comparisons that make the answer credible

Test tuned streaming, complete shared residency where feasible, static partial
retention for larger working sets, and compact fixed batches. Retain a runtime
cache as a conventional comparator if the pilot shows it is viable at the new
record widths. Account for identifying hot data and managing its lookup table.
Include frequency per byte as the conventional partial-retention rule, following
DRIM-ANN's access-per-capacity precedent. Compare applicable blocked sparse
formats as well: SparseP's BCSR/BCOO kernels already reuse source-vector blocks.
Charge their conversion, padding and metadata; a scalar streaming comparison
alone cannot establish an advantage over published sparse reuse.
Every approach must preserve the same output, contribution multiplicity and
arithmetic semantics. Do not change precision to make an approach win.

Tasklets share the capacity limit, but each approach may allocate it differently.
Pin tasklet count initially; use a focused sensitivity check to distinguish a
policy benefit from a poor buffer/concurrency choice. Floating-point arithmetic
is software-emulated on UPMEM: report its instruction cost separately from the
integer pilot and do not infer FP32 performance from integer addition.

For the decision model, compare with a reuse-only threshold, a simple capacity-first
rule, a calibration-selected fixed approach, and a hindsight best feasible approach. The hindsight result
is a diagnostic lower bound, not an implementable selector. Include the cost of
collecting every model input; complete future-access knowledge is an inspection
expense rather than a free runtime feature.

The earlier selective-encoding idea remains an optional candidate: retain raw
IDs in low-reuse regions and dictionaries plus ordered slots in reusable ones.
Dictionary coding, segmentation, caching and fallback are established. Implement
this extension only if the standard approaches leave a meaningful gap; do not
make the thesis depend on inventing another mechanism.

## A bounded experimental route

First port and verify a small SpMV/SpMM pair against CPU reference outputs and
published kernel behavior. Select public inputs spanning source reuse and row
imbalance, record the selection criteria, and freeze separate calibration and
evaluation sets. Split by complete matrix/graph or request stream, not by nearby
rows or random seeds from the same source. Use synthetic structures only for
controlled explanations.

Then run targeted sweeps rather than crossing every variable with every other
one. Each plotted experimental sweep must contain at least five actual settings.
Initial capacity ratios such as `0.25, 0.5, 1, 2, 4` and record widths such as
`8, 16, 32, 64, 128` bytes are proposed settings, subject to alignment and build
feasibility. They are not new measured results. Define the capacity-ratio
denominator from a declared common allocation for required non-retention state;
also report each method's actual remaining capacity, since its metadata differ.

| Focused comparison | Hold fixed or explicitly account for | What it should establish |
| --- | --- | --- |
| Working-set size relative to usable WRAM | Reference count, width and generated reuse distribution as far as possible; disclose changes. | Where complete residency stops being feasible and whether partial retention helps. |
| Record width on a fixed sparse structure | Indices, contribution order and numeric type; report the changing arithmetic work and capacity. | Whether wider transfers justify reuse or consume its WRAM advantage. |
| Reuse and skew across worklists | Reference count, width and working-set size. | When saved transfers pay for lookup and metadata, and when static hot-data choices fail. |
| Work amount and valid uses | Separate longer worklists from repetitions; account for data refresh and plan invalidation. | When setup is repaid and how robust that estimate is. |

Prefer naturally occurring variation in public datasets for external checks;
use declared synthetic generators for controlled sweeps. Capacity, arithmetic
and locality can change together, so an application sweep is not automatically
a causal ablation. Keep the five-size pilot as context, but it varied destination
count rather than source working-set size and cannot answer the capacity question.

Repeated-use curves calculated from one timing are modelled scenarios, even
with five plotted counts. Check representative repeated invocations for correct
refresh and state handling before using the per-use model. A plotted curve of
measured totals needs five actually executed counts. Deterministic simulator
reruns establish reproducibility, not independent statistical samples; paired
comparisons should use distinct inputs, with CPU timing variability separate.

Finally freeze one small model and evaluate the held-out inputs. Report predicted
versus actual accounted time, correct and incorrect choices, budget violations,
worst slowdown and selection regret: `(chosen cost - best feasible cost) /
best feasible cost`, with the selector's observation cost included in the chosen
cost. Retain failures. If the rule only transfers within one sparse family,
state that restriction rather than claim cross-domain generality.

Do not launch the full grid before the first feasibility screen. Stop expanding
when simple residency or streaming resolves a scenario. Add the embedding check
only if it tests a question the sparse kernels do not. Preserve exact sources,
compiler/simulator revisions, input hashes, options, outputs and reproduction
commands, following the existing artifact format.

## Established work and the distinction still to establish

| Prior work | Established overlap | Required distinction for this study |
| --- | --- | --- |
| [PrIM](https://doi.org/10.1109/ACCESS.2022.3174101) | Broad UPMEM workload characterization, DMA and tasklet effects. | A general benchmark survey is already available. Test a particular local-memory decision and its out-of-sample usefulness. |
| [SparseP](https://doi.org/10.1145/3508041), §§3.1, 3.5 | Sparse layouts, block source reuse, partitioning and balance. | Selected CSR/BCSR source inspected in the audit. Compare applicable blocked reuse with format costs, not only scalar streaming. |
| [PyGim](https://doi.org/10.1145/3700434), §§3.2–3.3 | A calibrated cost model selects graph-aggregation partitioning and parallelism. | Kernel and tuner source inspected. Selection is established; the proposed distinction concerns local retention representations and still needs evaluation. |
| [DRIM-ANN](https://doi.org/10.1145/3712285.3759801), §§3.1–3.2 | Frequent table entries and high-access-per-bit data placed in WRAM. | Hot-data retention is established; include a frequency-per-capacity baseline. |
| [ATiM](https://doi.org/10.1145/3695053.3731096), §§5–7 | Generated transfers, WRAM tiles and schedule tuning; inspected evaluation uses regular tensor operations. | The evaluated scope differs from our irregular worklists. Compiler support for this exact choice remains untested; do not infer its absence. |
| [ALPHA-PIM](https://doi.org/10.1109/IISWC66894.2025.00030) | Input-dependent sparse/dense kernel selection and scratchpad/instruction costs. | Selecting a variant from workload characteristics is established. Compare the actual choice and evidence, not just its label. |
| [PIM-CACHE](https://arxiv.org/abs/2603.23762), §4.2; 2026 preprint | Unique blocks, ordered offsets and low-redundancy fallback at the CPU–MRAM boundary. | Compare the mechanism if using prepared batches; a different memory boundary alone does not establish novelty. |
| [VIPER](https://arxiv.org/abs/2608.23404), abstract and UPMEM case study; 2026 preprint | Architecture-aware PIM cost and break-even modelling. | A generic “when PIM pays” model is already covered. Assess held-out selection among MRAM–WRAM approaches under explicit resource limits. |
| [How the Dirty Set Moves](https://arxiv.org/abs/2610.19489), introduction and work model; 2026 preprint | Sparse schedule lifetime, setup-inclusive costs and structural predictions on CPUs. | Payback and negative reuse results alone are not new. Establish specific, reproducible DPU decision boundaries. |
| [Register Tiling for Unstructured Sparsity](https://doi.org/10.1145/3591302), abstract only | Sparse specialization, reuse and compression. | Inspect the full representation before making any prepared-batch mechanism claim. |

The [literature review](LITERATURE.md), [WRAM review](WRAM_PLACEMENT.md) and
[PIM–GPU assessment](PIM_GPU.md) record inspection limits and further sources,
including UpDLRM and RecNMP. This table identifies obligations, not proof of an
unoccupied research area. Before a final originality claim, check whether the
closest implementations and newer work already answer the same scoped questions.

## What we know and what the thesis would add

The retained experiments already show that fewer reads can lose after software
overhead, preparation can erase a kernel saving, and shared residency can beat
batching when the whole source table fits. At the largest tested size, residency
reduced simulated cycles by about 29–30% on the two small synthetic families.
This is one tested size, an integer aggregation kernel and a simulator result.
It does not establish a general capacity threshold or a standard-application win.

The intended addition is a reproducible map of the tested conditions, a small
validated recommendation model, and clear examples where a tempting approach
is not worth its cost. Those results could help an engineer decide which
implementation to try and which costs to measure before adopting it. They
would not claim ownership of SpMV, caching, batching or preprocessing.

The final narrative should follow **the memory problem → established approaches
→ the unresolved choice → controlled standard tasks → measured trade-offs →
validated recommendations and their limits**. Keep the recommendations conditional:
“on these inputs and this configuration” is useful when the conditions are clear.
A complete multi-DPU application, GPU integration, hardware timing validation
and an energy model are separate work, not implied by this plan.
