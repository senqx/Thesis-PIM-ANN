# Research plan: test the opportunity before designing the solution

**Status:** proposed protocol, 13 November 2026. No new performance results.
Freeze the workload split, baselines, budgets and decision rules after platform
feasibility and before inspecting final evaluation outcomes. Pilot observations
remain exploratory. [Literature positioning](LITERATURE.md) is provisional.

## Objective and scope

Investigate adaptive data movement and prefetching in a heterogeneous CPU–DPU
system, initially using identical UPMEM DPUs. Start with exposed indexed
accesses and worklists, then establish whether the mechanism transfers across
sparse operations and graph traversal. HNSW is not a required starting point.

The available path is **simulation with uPIMulator**, subject to its compiler
dependency and model audit. No UPMEM hardware or working SDK installation is
currently available; an archived SDK is a candidate installation route.
Consequently, simulated execution time and traffic are the initial outcomes.
Physical end-to-end performance and energy remain unvalidated. Keep energy as
an explicit evaluation requirement conditional on obtaining justified model
parameters or hardware access, rather than inventing an energy score.

## Research questions

| ID | Question | Evidence needed |
| --- | --- | --- |
| RQ1 | Which graph/workload characteristics help predict future accesses? | Compare cheap structural features (degree/segment length, active worklist size) and runtime features (index proximity, block reuse, recent useful-byte fraction). Measure out-of-sample value beyond runtime feedback alone. Include metadata and feature-extraction costs. |
| RQ2 | How can decisions adapt to graph structures and traversal phases? | Compare demand-only, fixed look-ahead, fixed transfer sizes, workload-selected fixed policies and phase adaptation. A fixed winner throughout execution is evidence against needing phase adaptation. |
| RQ3 | How should data be distributed across the host and DPUs? | Begin with standard contiguous and work-balanced partitions. Measure cuts, replicated state, imbalance and host traffic. A new partitioner is warranted only if these baselines expose an unresolved bottleneck. Differently capable DPUs are optional, explicitly modelled later. |
| RQ4 | How can movement and computation be coordinated to reduce idle time? | Measure demand/DMA waits, runnable tasklets, synchronization and phase completion. Test overlap through supported interfaces; charge any producer tasklet and queue storage to the policy. Include host coordination separately. |
| RQ5 | Can adaptation improve performance without excessive bandwidth and memory use? | Evaluate complete simulated execution under equal memory and traffic budgets, including policy costs; report failures and Pareto trade-offs. This is the acceptance condition for the whole project. |

These are connected questions around one mechanism, not five independent
systems to invent. RQ1 supplies information, RQ2 chooses an action, RQ3 fixes
where data resides, RQ4 determines whether early movement helps, and RQ5 judges
whether the result is worthwhile.

## A falsifiable hypothesis

For a declared class of exposed irregular accesses, an adaptive policy using
structure and runtime feedback reduces simulated execution time relative to
both a tuned fixed policy and conventional feedback alone, under the same
traffic and memory limits, after including policy and coordination costs.

The broad hypothesis fails its primary test if the candidate does not beat
those comparators on held-out workloads within the declared budgets. A benefit
limited to one graph type supports only that narrower result. If adaptation
only learns one constant configuration, report configuration selection rather
than phase intelligence.

Proposed engineering thresholds to settle before the final campaign:

- At least **5% lower** primary execution time relative to the strongest eligible
  comparator, with uncertainty reported across independent workloads/instances.
- No more than **10% additional local MRAM↔WRAM bytes** relative to the matched
  demand baseline; report each direction. Initially allow **no extra host↔DPU
  bytes** for a policy that only changes local fetching.
- A **16 KiB total per-DPU cap for policy buffers and metadata**, with the full
  program, tasklet stacks and other live state fitting shared 64 KiB WRAM.
  Give baselines the same available capacity, and report total WRAM/MRAM/host
  storage, replication and peaks. This cap is a proposed experimental setting,
  not a hardware requirement.
- Report every workload's regression; use a predeclared **5% slowdown limit**
  for a claim of robust deployment across the primary set. A fallback may reduce
  harm but does not guarantee this limit. Show its detection delay and failures.

These numbers are proposed practical criteria, not literature-derived limits
or promises. Also show zero-extra-traffic and other feasible budget points;
do not move the goalposts after seeing final results. A 5% simulated benefit
alone cannot establish a physical 5% benefit given model uncertainty.

**Traffic volume and bandwidth are different.** Transferring the same bytes in
half the time doubles the achieved transfer rate without doubling traffic.
RQ5 concerns unnecessary bytes, resource contention and capacity, alongside
rate limits. Do not add local and host bytes into a single reassuring total
that hides growth at the expensive boundary.

## Candidate design space

Observe only information available during the actual execution. Once an index
or adjacency block has been read, its addresses may justify a bounded window
of future transfers. Addresses behind an unresolved dependency are unavailable
unless an explicit speculative predictor is implemented and charged for errors.

Choose from a small set of legal transfer sizes and look-ahead depths, including
zero. Use sampled useful-byte/reuse information and worklist structure to admit
or suppress early transfers. Limit outstanding data with a finite queue and
buffer budget. Check whether this can be done more cheaply than a fixed policy.
Machine learning is an option only if it adds value over simple thresholds.

For graph updates, prefetched state may become stale. Start with immutable
adjacency and explicitly versioned/read-only phase inputs; preserve the
algorithm's visited-state, update and barrier semantics. Queue publication and
buffer ownership must be correct across tasklets. An address reordering may
not change the required answer or convergence rule.

## Experiments in order

| Stage | Work | Decision |
| --- | --- | --- |
| 0. Platform feasibility | Resolve compilation; run a tiny upstream example with reference output. Inspect DMA blocking, tasklet overlap, memory limits, host transfers and statistic units. Compare selected microbenchmarks with published characterization where configurations match. | Continue only with executable, understood model boundaries. SDK functional simulation alone is not timing validation. |
| 1. Opportunity | Sweep transfer size, tasklets and look-ahead on sequential, clustered-index, random-index and dependent-chain kernels. Vary reuse, available independent work and phase changes. | Is there a meaningful choice between policies within the resource budgets? If the strongest fixed policy dominates, stop designing adaptation for that class. |
| 2. Minimal policy | Implement only the smallest justified controller. Measure every counter/decision, buffer, extra transfer and synchronization cost. | Does it beat matched fixed and feedback-only baselines? Remove complexity that does not pay for itself. |
| 3. Transfer of the result | Use SpMV/indexed gather and BFS-style traversal. Include real inputs from structurally different graph/matrix families plus controlled synthetic cases. Hold out complete graphs/matrices, not merely queries on the same graph. | Claim cross-workload utility only if the mechanism transfers. Otherwise narrow transparently. |
| 4. System relevance | Compare standard partitions and several simulated DPU counts; expose communication-heavy negative cases. Use an audited host model and overhead ranges. | Determine whether local gains survive complete modelled execution. Defer heterogeneous DPU hardware and further algorithms unless the main finding requires them. |

Select exact inputs, seeds, sizes and starting vertices before final evaluation.
Include skewed/community graphs, low-degree high-diameter graphs, and irregular
inputs with little locality. PageRank or another traversal is an extension if
BFS/SpMV leave a specific phase question unresolved. Floating-point DPU costs
must be included when using SpMV; retain identical arithmetic across policies.

## Baselines and controls

1. **Optimized demand execution:** an established DPU implementation with legal
   batching, caching and tuned tasklet count; not deliberately tiny DMA reads
   everywhere. Also keep a matched policy-disabled variant for attribution.
2. **Fixed policies:** appropriate sequential read-ahead, indexed look-ahead and
   fixed block sizes, with identical buffer resources and equivalent semantics.
3. **Training-selected fixed policy:** one global choice and a stronger
   per-workload/configuration choice selected from calibration executions.
   Charge calibration cost. Freeze choices before final evaluation.
4. **Runtime-feedback policy without graph features:** an implementable analogue
   of conventional throttling. Explain differences from CPU hardware schemes;
   do not label an adapted software baseline a reproduction of the original.
5. **Closest applicable implementation:** PrIM for execution/microbenchmarks,
   SparseP for SpMV, and other graph code if its algorithm is selected. Match
   data types, work, resources and compiler settings. Unsupported ports remain
   a limitation rather than a reason to claim a win over an untested system.
6. **Diagnostic hindsight choice:** optional bound showing the best fixed or
   phase choice with future knowledge, labelled nonimplementable. Never use
   hindsight labels to tune the final policy on evaluation inputs.

Use ablations to distinguish structure, runtime feedback, look-ahead, transfer
size and overlap. Keep partition and algorithm fixed for the main policy
comparison, then vary placement as a separate sensitivity. A CPU-only reference
checks answers; comparing CPU wall-clock time with simulated DPU time requires
an explicitly justified system model and cannot establish measured acceleration.

## Measurement and reproducibility

The primary system boundary starts with input in host memory and ends when
the correct output is available to the host. Include placement/loading,
launches, DPU execution, exchanges, host work and final transfer where modelled.
Also report resident-data execution separately, and amortize one-time costs
over a declared number of repeated uses. Until the host path is validated,
call the result **DPU kernel time plus disclosed communication/host estimates**,
not complete application latency. Never use the simulator's own wall-clock
runtime as the target program's execution time.

Record cycles and modelled time with clock domains, bytes by movement boundary
and direction, transfer counts/sizes, tasklet waits, maximum buffer occupancy,
useful/unused prefetched bytes, late arrivals, and policy instruction cost.
Define usefulness over a declared buffer lifetime; count alignment, padding,
metadata, writebacks and retries. A prefetch that arrives too late may still
serve demand and must not be double-counted as a second transfer.

Simulator-side observation counters can be cost-free instruments, but any
counter a deployable policy reads must have a real implementation and cost.
Keep those two roles separate. Compare answers against a reference; test
dependency order, bounds, barriers and traffic accounting before performance.

Pair policies on the same workload instances and seeds. Separate simulator
determinism from workload variation: rerunning a deterministic simulation does
not create independent evidence. Report paired per-instance ratios, absolute
differences, family-level summaries and uncertainty at the independent-input
level. Size the final sample from pilot variability and desired precision;
do not assume ten runs is automatically sufficient. Record exploratory tuning,
failed runs, exclusions and all primary comparisons.

Pin simulator/toolchain commits, configurations, dataset versions/licenses and
hashes; record commands and machine details. Generate figures and tables from
retained raw results. Separate a small reproduction check from the full matrix.
Any simulator modification needs a reviewable patch, semantic tests and an
updated fidelity statement. Published uPIMulator validation errors are not
per-workload confidence intervals; vary uncertain timing/communication
parameters and check whether recommendations survive.

For energy, report joules only from measurements or a documented, applicable
model with execution, transfer and static-power terms. Run parameter
sensitivity and identify the accounting boundary. Fewer transferred bytes are
evidence of lower traffic, not proof of lower energy. Without such a model,
retain energy as an unanswered question.

## Completion criterion

A defensible thesis identifies an applicable workload class, establishes the
costs and limits of a reproducible mechanism against strong baselines, and
states whether the hypothesis survived. It need not solve all irregular access.
If the natural aggressive policy fails and a simpler fixed policy works better,
that is a valid scoped result. It is not proof that all adaptive prefetching is
impossible, and positive alternatives cannot be promised before evaluation.
