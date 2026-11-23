# Research direction: choosing WRAM reuse under explicit costs

23 November 2026. **Proposed continuation; novelty remains to be established.**
The [short thesis](../thesis/short-thesis.md) integrates the completed experiments.
This note specifies the remaining questions and the evidence needed to answer
them. The [baseline controls](../experiments/baseline-gates/README.md) favor
shared residency for the small tables and strengthen compact fixed batching.
The next opportunity concerns working sets larger than available WRAM.

## The engineering question

An engineer has a known graph-aggregation worklist and a small WRAM budget.
Should the program stream source values, retain them in WRAM, or prepare
batches that reuse them? The useful answer must account for the instructions
needed to manage reuse, metadata transfers, competing uses of WRAM, and how
many times the worklist will be executed before it changes.

**Proposed objective:** develop and evaluate a method for selecting streaming
or prepared reuse for repeated graph aggregation on UPMEM, while fitting the
same WRAM capacity and not increasing installed index bytes or local read
bytes relative to a matched compressed-index streaming baseline.

These byte constraints are stricter than a latency-only objective. They are
not claims about achieved bandwidth, energy, or hardware execution time.
Preparation, temporary host storage and any retained host copy must also be
reported; reducing installed bytes must not conceal extra host resources.

## Three connected research questions

### RQ1 — Predict the benefit

**Which observable access and resource characteristics predict whether WRAM
reuse reduces complete execution time, beyond simply counting saved reads?**

Deliver a small decision model that accounts for transfers, metadata decoding,
tasklet concurrency and WRAM allocation. Test it against a reuse-only rule and
a calibration-selected fixed policy on unseen inputs. Existing pilots identify
relevant costs; they do not establish a predictive rule or isolate every cause.

### RQ2 — Respect the budget

**Can selectively preparing reusable regions improve execution without
increasing installed index bytes or local reads, while fitting the same WRAM
limit?**

Deliver an executable representation and planner with explicit byte/capacity
checks. Compare it with compact streaming, fixed batches and applicable static
retention. Keep unmodified streaming available. Compact dictionaries now meet
the storage budget on some inputs, but not all. Selective preparation and a
budget-enforcing planner remain unimplemented.

### RQ3 — Repay preparation

**How many valid uses are needed to repay inspection, preparation and
installation, and can short-lived work be correctly rejected?**

Compare total accounted cost over declared plan lifetimes, including inspection
on rejected inputs and the cost of wrong predictions. Report break-even values
and their sensitivity to preparation and transfer costs. Current estimates
combine Python preparation with simulated kernels; they are specific results,
not a deployment threshold for the proposed planner.

The causal path is **understand the costs → choose an affordable execution
representation → establish when the choice repays its preparation**. RQ2 is
the proposed implementation contribution. RQ1 explains and tests the decision;
RQ3 determines whether it is useful. A new name for these questions would not
establish novelty: the mechanism comparison and experimental answers must do
that work.

## Candidate mechanism, in ordinary terms

Inspect a known worklist before execution. Leave regions with little useful
reuse as ordinary source IDs. Encode selected reusable regions as unique IDs
plus an ordered list of WRAM slots. A candidate planner may choose boundaries
and batch lengths, instead of always making every 64 references a batch.

The planner first checks exact storage, read and capacity costs, including
mode tags, headers, offsets, alignment and tasklet padding. Among feasible
choices, it uses a calibrated execution-cost estimate and the expected number
of valid uses. If none is worthwhile, the complete worklist uses the original
streaming representation and kernel. Inspection cost still counts in this case.

Dictionary coding, segmentation, cost modelling and fallback are established
ideas. The proposed research concerns their concrete interaction at the
MRAM–WRAM boundary on UPMEM, with a tested representation and enforceable
resource limits. Neither a new general compression algorithm nor a universal
prefetcher is claimed. Exact byte bounds do not imply a no-slowdown guarantee.

Preserve reference order and multiplicity. Reload current feature values on
each invocation; only access metadata are reusable. Initially assume fixed
connectivity, order, feature width and tasklet assignment during a declared
plan lifetime. Dynamic graph repair and prediction of unknown frontiers are
outside this continuation.

## Closest work and the specific distinction to test

| Prior work | Established overlap | Remaining comparison for this proposal |
| --- | --- | --- |
| [SparseP](https://people.inf.ethz.ch/omutlu/pub/SparseP-SpMV-in-Real-Processing-in-Memory-Systems_pomacs22-arxiv22.pdf), §§3.1, 3.5 | Efficient sparse access, compressed storage, chunked metadata and amortized setup. | Determine whether prepared source reuse beats an appropriately matched established sparse kernel, including feasible static residency. |
| [PyGim](https://arxiv.org/abs/2402.16731), §§3.2–3.3 | UPMEM graph aggregation, WRAM accumulation, partitioning and performance-guided tuning. | Its inspected kernel discussion does not answer the proposed per-region source-reuse representation question under a no-growth index budget. Check the relevant implementation before claiming a distinction from the system. |
| [ATiM](https://doi.org/10.1145/3695053.3731096), §5 | Generated data transfers, local-memory tiles and schedule tuning. | Establish whether its irregular-access support can express equivalent reuse, and whether the proposed representation or decision rule adds anything. This is still a novelty gate. |
| [PIM-CACHE](https://arxiv.org/abs/2603.23762), §4.2 and fallback discussion; 2026 preprint | Unique blocks plus ordered offsets; content-based CPU-to-MRAM transfer reduction; proposed low-redundancy fallback. | Our candidate reuses source records within WRAM and keeps plans valid when feature values change. Compare metadata/decision mechanisms, not just their different memory boundaries. |
| [VIPER](https://arxiv.org/abs/2608.23404), abstract and UPMEM case study; 2026 preprint | Architecture-aware PIM cost modelling, offloading and break-even predictions. | A generic PIM cost model is not our contribution. The proposed model must resolve decisions among local irregular-access representations and be tested for that purpose. |
| [How the Dirty Set Moves](https://arxiv.org/abs/2610.19489), introduction and work model; 2026 preprint | Preparation lifetime, retained sparse schedules, setup-inclusive costs and structural prediction for incremental CPU sparse multiplication. | Plan lifetime and a negative result for reuse are not new by themselves. Our scope is fixed-worklist DPU execution with explicit local capacity and byte constraints. |
| [Register Tiling for Unstructured Sparsity](https://doi.org/10.1145/3591302), publisher abstract only | Sparse-pattern specialization, reuse and compression for CPU/ARM execution. | Inspect the full representation and transformations before claiming that the batch mechanism is distinct from existing sparse compilation. |

This focused review supports a **candidate question not answered by the
inspected passages**. It does not prove an absence across the literature.
The last column records obligations, not completed novelty checks. A further
2026 discovery, [DyPamear](https://doi.org/10.1145/3770743.3804278), already
targets dynamic graph mining on UPMEM; its publisher abstract was inspected.
It is another reason not to expand casually into general dynamic-graph claims.

## Baseline gates and remaining controls

1. **Use equivalent index widths.** The original batch dictionary stored
   32-bit source IDs while streaming used 16-bit IDs. The latest screen gives
   both methods 16-bit IDs. Keep that compact fixed-batch control when testing
   selective planning.
2. **Test complete residency where feasible.** The synthetic feature table is
   only `512 × 8 = 4,096` bytes. A shared read-only WRAM preload may fit with
   smaller streaming buffers. Check actual linkage, initialization, barriers
   and complete cycles. At the largest tested size, shared preload beats both
   streaming and batching on those synthetic inputs. Include working sets
   larger than available WRAM; varying destination count alone does not
   establish this.
3. **Compare against simpler decisions.** Include tuned streaming, applicable
   static retention, compact fixed batches, a reuse-threshold selector and a
   calibration-selected fixed policy. Use a hindsight choice only as a labelled
   diagnostic. If a simple rule matches the candidate, prefer that outcome.
4. **Measure comparable preparation.** Use comparable native host encoders
   for the eventual practical-cost claim. Retain Python timings as reference
   results. Charge sampling/inspection even when preparation is rejected.

## A bounded route to an answer

Resolve the mechanism-level prior-art checks and extend the baseline controls
to working sets larger than available WRAM. The small-table screen already
favors ordinary shared residency over batching. Stop designing the planner if
conventional compression or feasible residency resolves the remaining opportunity.

If a useful choice remains, implement one selective representation and one
small cost model. Freeze the model and evaluation protocol before testing on
held-out graphs. Match logical work, arithmetic and resource ceilings. Include
low-reuse and mixed-reuse streams and more than one real graph; keep all
regressions. Use at least five actual settings for each plotted sweep, with
modelled reuse scenarios labelled separately from executed simulations.

Test mechanism ablations that change one cause at a time. For example, compare
compact fixed batching with selective batching at the same index width, and
compare the cost model with a reuse-only rule using the same available choices.
Success requires useful predictions and complete-cost improvements beyond
these controls, not merely fewer bytes or a win over the original prototype.

This remains a single-DPU study of repeated graph aggregation. Simulation
results require model-sensitivity checks and an explicit hardware-validation
limit. Multi-DPU placement, GPU integration and energy claims are separate
work. A useful negative answer must identify the tested alternatives and
conditions; it cannot prove that WRAM reuse is universally ineffective.

The intended contribution, if supported, is an implementation and decision
rule that lets another engineer determine **when prepared WRAM reuse is worth
using under a fixed resource budget and a finite plan lifetime**. The current
pilot justifies investigating that contribution; it does not yet deliver it.
