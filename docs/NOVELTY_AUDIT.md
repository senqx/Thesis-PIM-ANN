# What does this thesis contribute?

**Targeted novelty audit — 24 November 2026.** This assesses the current
[thesis draft](../thesis/short-thesis.md) and [proposed continuation](CONTRIBUTION_PLAN.md).
It adds no performance experiments and makes no claim of exhaustive coverage.

**Experimental follow-up:** the [standard-workload study](../experiments/decision-study/README.md)
now implements the missing baseline, capacity, native-cost and held-out checks.
The frozen model finds an equally fastest feasible kernel in 8/24 conditions
and fails the practical-success criterion at all tested lifetimes. The completed
contribution is scoped comparative evidence and a negative result for this
selector, alongside positive static-retention regimes. It does not establish
a new algorithm or a successful general adaptive framework. The audit below
preserves the assessment and obligations that motivated that experiment.
The [post-freeze correction](../experiments/decision-study/corrected/README.md)
updates native costs and decision accounting without changing the cycle model,
workloads or this scoped contribution claim. Corrected host-cost results are
not a new untouched confirmation. Direct header checks improve the simple
baselines; both charged and zero-selection-overhead model choices still fail
at all eight reference lifetimes. Free per-input refresh-time knowledge is an
explicit optimistic assumption, not an additional deployable contribution.

## What the completed follow-up adds

| Closest established idea | This thesis's tested addition | What is not claimed |
| --- | --- | --- |
| SparseP's blocked source reuse | Matched scalar/vector comparisons of 2x2/4x4 blocked formats, streaming and retention, including padding, native conversion and per-input byte limits | A new sparse format or a speedup over the complete SparseP system |
| DRIM-ANN's hot-data placement | A measured boundary: frequency retention helps at 16-byte records on four held-out sparse structures but loses at 128 bytes on the primary configuration | Inventing hot placement or proving a universal footprint threshold |
| PyGim/ATiM's cost-based tuning | A frozen local-representation selector tested against direct simple rules with visited-candidate costs charged; the selector fails | Inventing autotuning or demonstrating a successful adaptive framework |
| Existing preprocessing/payback analyses | Native preparation/refresh measurements, explicit transfer scenarios, remaining cost margins and observed timing sensitivity for these implementations | Inventing amortization or measuring whole-application performance |

The useful result is a reproducible decision study with both favorable regimes
and failures. It tells an engineer which comparison can change a recommendation,
how resource limits remove a seemingly faster choice, and why a more elaborate
selector is unjustified here. This is an empirical Master's-level contribution.
The inspected literature supports that positioning; it does not certify that
no paper has ever reported a similar crossover. Neither changing benchmarks nor
obtaining a negative result automatically establishes publication priority.

Current RQ status: RQ1 has standard-operation and controlled-boundary evidence;
RQ2 has native costs and conditional payback/margin estimates; RQ3 has a completed
held-out evaluation that rejects the tested selector. See the
[gap-closure record](GAP_CLOSURE.md) for evidence and remaining limits. The sections
below retain the earlier audit's prospective wording as a historical record.

## Verdict before the follow-up

**The project has reproducible exploratory findings, but has not yet established
a novel algorithm or a validated general decision rule.** Its strongest possible
contribution is a tested explanation of when established local-memory approaches
are worth using on UPMEM. That contribution still needs evidence beyond the pilot.

The distinction matters: implementing something ourselves gives us an artifact;
measuring it gives us results; establishing something useful that prior work did
not already answer requires a comparison with that work. A different benchmark
or memory boundary does not, by itself, establish originality.

## What is already known

MRAM is a DPU's large local DRAM bank; WRAM is its small, explicitly managed
working memory. Keeping useful values in WRAM, grouping accesses and predicting
which configuration will be faster all have close precedents.

| Proposed claim | Closest inspected evidence | Consequence |
| --- | --- | --- |
| Keep frequently used data in WRAM. | [DRIM-ANN](https://doi.org/10.1145/3712285.3759801), §§3.1–3.2, places frequent squaring-table entries in WRAM and ranks data by average accesses per bit. | Hot-data retention is established. Compare against frequency per byte, including selection and lookup costs. |
| Reuse sparse source values instead of loading them repeatedly. | [SparseP](https://doi.org/10.1145/3508041), §3.5, and its BCSR implementation reuse source-vector blocks across rows within a block. | A scalar streaming baseline is insufficient. Include applicable blocked formats and their conversion, padding and storage costs. |
| Predict a useful PIM configuration from input and hardware properties. | [PyGim](https://doi.org/10.1145/3700434), §3.3, calibrates hardware costs and predicts partitioning and parallelism choices, accounting for transfers, execution and merging. | A calibrated cost model or input-dependent selection is not new in itself. Our candidate concerns the choice of local source-retention representation. |
| Tune WRAM buffering and concurrency. | [ATiM](https://doi.org/10.1145/3695053.3731096), §§5–7, jointly tunes caching tiles, tasklets and DPU counts. | Buffer tuning is established. Its inspected evaluation covers regular tensor operations and layers, not our irregular worklist comparison; that does not prove the compiler cannot express it. |
| Different workloads favor caches or scratchpads. | [Pathfinding Future PIM Architectures / uPIMulator](https://doi.org/10.1109/HPCA57654.2024.00029), §V-D, demonstrates both outcomes. | Workload dependence is already known. Its cache is a simulated hardware alternative, not a software cache available on stock UPMEM. |
| Prepare unique data plus ordered references, with a fallback. | [PIM-CACHE](https://arxiv.org/abs/2603.23762v2), §4.2, uses unique blocks and ordered offsets for host-to-MRAM transfer. | Dictionary-and-slot representations and low-redundancy fallback are not sufficient mechanism claims. Different transfer boundaries change costs, not automatically originality. |
| Account for preparation and determine when PIM or preprocessing pays off. | [VIPER](https://arxiv.org/abs/2608.23404v1), UPMEM case study; [How the Dirty Set Moves](https://arxiv.org/abs/2610.19489v1), introduction and work model. | Generic break-even analysis, sparse schedule lifetime and negative reuse results are established. These inspected 2026 sources are preprints; peer review is not established here. |
| Interleave software-controlled transfers and computation near memory. | [PUL](https://doi.org/10.1007/978-3-032-05281-0_4), §§2–3, studies UPMEM tasklets and a separate FPGA platform with custom asynchronous DMA. | Software preloading is established. The FPGA interface must not be attributed to stock UPMEM; its UPMEM discussion uses tasklet concurrency. |

These overlaps do not make our measurements worthless. They rule out broad
claims such as “we introduce adaptive PIM data movement” or “we discover that
reuse has overhead.” The useful remaining question is whether a particular
decision can be explained and predicted better than existing alternatives.

## Pilot evidence at the audit checkpoint

The [five-size study](../experiments/access-plan-fivepoint/README.md) and
[baseline controls](../experiments/baseline-gates/README.md) provide matched
implementations, preserved inputs and executable simulation artifacts. Together
they contain 194 distinct configurations, not 194 independent workloads.

1. **A concrete limit on prepared batching.** At 3,072 destinations, compact
   batch64 reduces complete simulated cycles by 6.18% on community inputs and
   6.10% on sampled ca-GrQc inputs, but increases them by 41.31% on uniform
   inputs. These are paired means over two seeds against the best tested
   streaming buffer, not application speedups or a universal method ranking.
2. **A baseline that changes the decision.** Loading the entire 4 KiB synthetic
   source table into shared WRAM reduces cycles by 29.10% on community and
   29.63% on uniform inputs. The batching improvement over streaming therefore
   does not establish a benefit over the best tested feasible alternative.
3. **Evidence that a cycle improvement may fail a resource constraint.** One
   compact ca-GrQc input increases installed metadata by 1.17%. It fails the
   zero-growth requirement despite faster simulated execution. The mean over
   seeds would obscure that violation.
4. **Explicit costs and reproducibility.** The original Python preparation
   implementation needs approximately 72–99 valid uses in its largest positive
   cases to repay preparation alone. Installation is additional. Pinned images,
   counters, outputs and accounting let others examine these conditional claims.

These are new measurements produced by this project and useful checks against
misleading comparisons. **They do not yet establish a new scientific principle
or priority over the literature.** The “whole table fits” result is a necessary
control, not an invention. The preparation thresholds describe the original
Python implementation, not optimized native preparation or compact batching.

The pilot scope was one simulated DPU, twelve tasklets, 8-byte integer records
and sampled fixed-degree aggregation. The community generator favors reuse
within the tested batches; sampling with replacement can add repeated neighbors.
Increasing destination count did not sweep source-table capacity. Partial
residency, standard SpMV/SpMM, a frozen selector, hardware timing and energy
were untested at that checkpoint. The completed follow-up is summarized above;
see the current [validation record](VALIDATION.md).

## The candidate contribution proposed at that checkpoint

> Determine and predict when streaming, full or partial WRAM retention, and
> prepared batches minimize the accounted cost of indexed aggregation on a
> fixed UPMEM configuration, under a shared WRAM limit, explicit traffic and
> storage budgets, and a declared number of valid uses of the preparation.

This is a **research objective**, not a result already achieved. “Accounted
cost” includes inspection, construction, installation, complete DPU execution
and data refresh. Without hardware, installation assumptions and totals mixing
host measurements with simulator times must remain labelled as models.

The potential addition beyond PyGim's partitioning/parallelism tuner is evidence
about choosing the local source representation. Beyond DRIM-ANN's hot-data
placement, it is evidence about when partial retention loses to streaming or
prepared batches after all relevant costs. Beyond SparseP, it must explain
whether there is a remaining advantage over applicable blocked source reuse.
None of these comparisons has yet demonstrated that addition.

An engineer should eventually be able to use the result to decide:

- Whether fitting a useful subset in WRAM is worth its lookup and loading cost.
- Whether reuse occurs close enough together for small batches to exploit it.
- Whether the workload will remain valid long enough to repay preparation.
- Whether the saving survives a byte budget and prediction uncertainty.

The deliverable would be a measured map of those decisions and a small rule
validated on inputs excluded from model development. Merely combining these
questions into one table would not be enough. The study must identify conditions
that change a decision, explain why, and test whether that knowledge transfers.
It would not establish a general CPU/GPU/PIM offload rule or energy efficiency.

## Minimum evidence needed to establish that contribution

**First, close the baseline gap.** Compare tuned streaming, feasible full and
frequency-based partial residency, compact batching, and applicable blocked
sparse reuse. Give them the same total WRAM ceiling and comparable tuning.
Include linked stacks, buffers and lookup metadata. Charge every method for
its preparation and any extra storage or transferred bytes. If a representation
violates the primary byte budget, retain its unconstrained result and label it
ineligible for the constrained comparison.

**Second, test the proposed boundary.** Use a small declared set of public
SpMV/SpMM inputs, plus controlled cases spanning usable WRAM capacity and
record width. Keep at least five executed settings in each claimed experimental
sweep. These two operators share sparse structure; their names do not prove
generality across unrelated applications. Use comparable native preparation
for practical payback estimates, and account for changes that invalidate plans.

**Third, test an actual recommendation.** Freeze a simple rule before evaluating
complete held-out matrices. Compare it with a reuse-only rule, a simple
capacity-first rule, a calibration-selected fixed method and the best feasible
method known after measuring all choices. Count observation/selection costs.
Report wrong decisions, worst slowdown, byte violations and selection regret:
the excess cost relative to the best feasible method for that input.

**Finally, use a stopping rule.** If a simple established method or rule performs
equally well, do not add adaptive machinery to manufacture a contribution.
Report the bounded characterization or replication result and its limits. If
the study finds a reproducible crossover that simpler rules miss, and a small
model predicts it on held-out inputs, that supports the intended empirical and
decision-guidance contribution. Neither outcome automatically establishes
publication priority; compare the final result with the closest methods again.

At the audit checkpoint the RQs had different statuses: RQ1 had pilot observations,
RQ2 has implementation-specific estimates, and RQ3 has no evaluated selector.
Completing those tests required research work, not a wording change; the follow-up
above records their outcomes.

## Inspection record and limits

This audit read relevant full-paper sections and selected official source files;
it did not run or reproduce the competing systems. Source inspection included:

| Artifact | Pinned source inspected | What it verifies |
| --- | --- | --- |
| SparseP | Revision `2cbd2217fc1da7fe97da78079ae4e4db396ff400`: [CSR](https://github.com/CMU-SAFARI/SparseP/blob/2cbd2217fc1da7fe97da78079ae4e4db396ff400/spmv/1D/CSR-nnz/dpu/task.c) and [BCSR](https://github.com/CMU-SAFARI/SparseP/blob/2cbd2217fc1da7fe97da78079ae4e4db396ff400/spmv/1D/BCSR-nnz/dpu/task.c) kernels. | Direct source loads in CSR and block source loads reused across rows in BCSR. |
| PyGim | Revision `22ea1cb0a870a61f7a63c992d4098671629d081a`: [CSR kernel](https://github.com/CMU-SAFARI/PyGim/blob/22ea1cb0a870a61f7a63c992d4098671629d081a/backend_pim/spmm_default/dpu_kernels/spmm_mul_csr_dpu.c) and [tuner](https://github.com/CMU-SAFARI/PyGim/blob/22ea1cb0a870a61f7a63c992d4098671629d081a/utils/autotuner.py). | Source-row loading and explicit load/compute/retrieve/merge cost selection. This is not an exhaustive audit of every kernel path. |
| ATiM | Artifact revision `4d6dc5d8cce9647a5a44facd4d237bff7e8e56e8`: [benchmark definitions](https://github.com/SNU-CODElab/atim/blob/4d6dc5d8cce9647a5a44facd4d237bff7e8e56e8/evaluation/bench.py) and README; paper §§6–7. | Regular tensor benchmark definitions and published evaluation scope. Compiler expressiveness for our worklists was not tested. |

Public reading copies: [PyGim v7](https://arxiv.org/abs/2402.16731v7),
[DRIM-ANN v2](https://arxiv.org/abs/2410.15621v2),
[ATiM v3](https://arxiv.org/abs/2412.19630v3),
[uPIMulator v3](https://arxiv.org/abs/2308.00846v3) and
[PUL v1](https://arxiv.org/abs/2506.16976v1).

Additional overlap was checked at abstract level only for
[A Full-System Perspective on UPMEM Performance](https://doi.org/10.1145/3609308.3625266)
and [Register Tiling for Unstructured Sparsity in Neural Network Inference](https://doi.org/10.1145/3591302).
Their publisher PDFs returned HTTP 403. The former's abstract reports that
full offload accounting reverses many kernel-level recommendations; the latter
describes sparse specialization and register reuse. Neither abstract establishes
the details of a matching local-memory policy.

Discovery also used OpenAlex searches for “UPMEM WRAM cache,” “UPMEM scratchpad
reuse prediction,” “UPMEM data reuse inspector executor” and “UPMEM software
cache locality,” alongside the existing [literature review](LITERATURE.md).
Selected results were inspected, not every indexed paper. No exact match found
in these sources would be evidence of limited search coverage, not proof that
our candidate is the first. The novelty claim must remain conditional until
the specific result and comparison are complete.
