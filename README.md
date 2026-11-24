# When is WRAM reuse worth it?

Master's research by **Artashes Atanesyan**.

**[Read the thesis draft (PDF)](thesis/short-thesis.pdf)** ·
[Markdown version](thesis/short-thesis.md) ·
[Research questions](docs/CONTRIBUTION_PLAN.md) ·
[Validation record](docs/VALIDATION.md)

When does keeping indexed data in a DPU's small working memory save more time
than it costs to manage? This project investigates that question using
compiled UPMEM programs, reproducible simulations and explicit accounting
for preparation, memory capacity and data movement.

The thesis is **an experimental investigation of the costs and benefits of local
data reuse on UPMEM**. Its central question is whether a saving survives the
work required to obtain it.

**Research revision — 24 November 2026:** the follow-up implements standard
integer SpMV/SpMM, stronger baselines, native preparation and a cost model
frozen before held-out evaluation. It asks **when each approach is worth using,
and in which scenarios**. The tested selector fails its practical-success
criterion; the thesis reports that result alongside useful static-retention
regimes. Hardware speedup, energy savings and complete application acceleration
have not been demonstrated.

**Preparation/accounting correction:** current totals use freshly measured native
costs and decision paths that include rejected candidates while skipping
unnecessary inspection. All 511 archived invocation inputs match the corrected
preparation byte for byte. The DPU cycles and frozen model are reused; the
[correction record](experiments/decision-study/corrected/README.md) separates this
post-freeze correction from the historical measurements.

## What the experiments show

UPMEM is a near-memory form of processing-in-memory. Each DPU has a large
local DRAM bank (**MRAM**) and a small, software-managed working memory
(**WRAM**). Its hardware threads, called tasklets, share that WRAM.

The [standard-workload study](experiments/decision-study/README.md) compares
seven configurations on complete sparsity patterns from seven public matrices.
Three matrices calibrate the model; four are held out. SpMM has five executed
record widths, and two controlled input families have five source-table sizes.
The original graph-aggregation pilot remains available as earlier evidence.

| Finding | Evidence and interpretation |
| --- | --- |
| Static retention has useful regimes. | At eight tasklets and 16-byte records, frequency-based retention saves 11.97–15.71% of complete simulated cycles on the four held-out matrices without growing installed metadata or local traffic. |
| A wider record can change the answer. | At 128 bytes, the same retention policy is slower on all four matrices; streaming is the best feasible tested choice. |
| Adaptive selection must repay its own work. | Counting exact ties, the frozen model finds a fastest feasible kernel in 8/24 matrix/shape conditions. It fails the practical-success criterion at all eight tested modelled lifetimes after its costs are included. |
| Setup is implementation-dependent. | Native costs replace the pilot's Python-only payback estimates for the new kernels. Host transfer and launch assumptions remain explicit scenarios. |
| Stronger baselines and resource limits matter. | Full retention, frequency placement and 2x2/4x4 blocked reuse are compared. Faster over-budget cases remain visible; feasible tasklet configurations get a separate robustness check. |

The contribution is **a reproducible comparison of when established choices
help, lose or violate a resource budget, and a held-out negative result for the
tested selector**. The algorithms themselves are credited to prior work.
The [novelty audit](docs/NOVELTY_AUDIT.md) states that distinction explicitly;
the [paired results](experiments/decision-study/corrected/results.md) provide the numbers.
The model's failure does not prove that every adaptive policy must fail.

## Current study and future directions

| Stage | Question | Status |
| --- | --- | --- |
| 1. Understand local retention | When do saved transfers repay execution, retention and access-plan preparation costs? | Current thesis; tested within the declared simulator and accounting scope |
| 2. Predict future requirements | Can topology and traversal state predict useful accesses before they are revealed? | Possible next research; requires new workloads and evaluation |
| 3. Coordinate heterogeneous movement | Where should data reside, which processor should execute the work, and when should transfers occur? | Longer-term direction; requires system-level placement, scheduling and communication evidence |

The tested selector belongs to Stage 1: it chooses an implementation for a known
worklist. Predicting its execution cost is different from predicting future
addresses. The later stages are research directions, not deliverables established
by this paper.

The failed-selector result is central: **an optimization can reduce movement and
repay preparation, while an adaptive mechanism for selecting it still costs more
than a simple fixed policy**. In this study, both inspection overhead and wrong
performance rankings contribute. All tested methods preserve correct outputs;
the failure concerns the quality and cost of the recommendation.

## Read in this order

| Document | What it gives you |
| --- | --- |
| [Thesis draft](thesis/short-thesis.pdf) | Concepts, worked example, prior work, RQs, completed evidence, costs and limitations |
| [Standard-workload results](experiments/decision-study/corrected/results.md) | Measured boundaries, native-cost accounting and held-out selection results |
| [Study protocol](experiments/decision-study/PROTOCOL.md) | Questions, frozen split, resource budgets and success criterion |
| [Novelty audit](docs/NOVELTY_AUDIT.md) | Established mechanisms, the completed empirical contribution and limits of the originality claim |
| [Five-size experiment](experiments/access-plan-fivepoint/README.md) | Original batching curves, CPU preparation timings and replay instructions |
| [Baseline controls](experiments/baseline-gates/README.md) | Compact dictionaries, shared residency and the updated recommendation |
| [Literature review](docs/LITERATURE.md) | Reading links, established techniques and limits of the novelty assessment |
| [Platform setup](docs/PLATFORM.md) | Pinned compiler/simulator, setup commands and timing-model limitations |

Supporting material preserves the [first residency pilot](experiments/wram/README.md),
[prepared-access experiments](experiments/access-plan/README.md),
[three-size checkpoint](experiments/access-plan-scaling/README.md),
[WRAM placement literature](docs/WRAM_PLACEMENT.md), and
[CPU-mediated PIM–GPU feasibility](docs/PIM_GPU.md).
The [original broader proposal](docs/RESEARCH_PLAN.md) and subsequent
[contribution plan](docs/CONTRIBUTION_PLAN.md) are retained for context.

## Check and reproduce the evidence

Run the retained-record audits with Python 3, from the repository root:

```sh
python3 scripts/access_plan_fivepoint.py verify
python3 scripts/access_plan_gates.py verify
python3 scripts/decision_artifact.py verify
python3 scripts/decision_correction.py verify
```

These commands check hashes, counters, matched work and output records.
After setting up the [pinned Go uPIMulator](docs/PLATFORM.md), freshly execute
representative archived programs:

```sh
python3 scripts/access_plan_fivepoint.py replay
python3 scripts/access_plan_gates.py replay
python3 scripts/decision_artifact.py replay
```

Frozen replay needs neither the compiler SDK nor a graph download. Use a fresh
destination for each replay; the artifact READMEs give complete commands.
[Document build instructions](thesis/README.md) describe how to regenerate
the figures and PDF. The [build record](thesis/build.json) contains the actual
page count and the corresponding source, figure and PDF hashes.

The five-size artifact contains **180 configuration records** and **1,320 CPU
timing samples**. The baseline artifact contains **14 new executions plus 24
reused comparators**: 194 distinct configurations across these two artifacts.
The earlier 108-record size checkpoint is included in the 180, not additional
evidence. Record and timing counts are not counts of independent statistical
experiments. Earlier pilot artifacts remain separately identified.

The new decision-study artifact contains **485 distinct simulation records** and
**511 kernel invocations**, including correctness and robustness checks. Its
23,040 cost scenarios are calculations over retained evidence, not additional
simulator experiments. The correction adds **446 native preparation cases**,
with 31 retained timing samples each; it does not add independent workloads.
Four representative records were replayed again. The [inventory](experiments/decision-study/README.md)
and [gap-closure record](docs/GAP_CLOSURE.md) give the breakdown and remaining limits.

## Scope and provenance

The main study uses one simulated DPU and eight tasklets, with four/twelve-tasklet
robustness checks. It executes integer SpMV/SpMM on small public sparsity patterns;
the original floating-point values are replaced by documented integer weights.
The earlier graph pilot uses twelve tasklets, two seeds per family and a sampled
real graph. Neither study executes complete GNN training. The Go simulator's
timing for these kernels has not been validated against hardware. GPU integration
and energy evaluation remain outside the completed work. The
[gap-closure record](docs/GAP_CLOSURE.md) separates completed checks from these limits.

The repository name is historical. The earlier HNSW/DRAM-service thesis and
its evidence remain in the
[archived revision](https://github.com/senqx/Thesis-PIM-ANN/tree/fcab5d2be844dd1097f7f0ae13bbe500a12f8caf).
[Previous results](docs/PREVIOUS_RESULTS.md) gives a concise summary and recovery
instructions. Dependencies and regenerable runs live in ignored directories.

## License

[MIT](LICENCE). Third-party software and datasets retain their own terms;
the experiment artifacts include attribution and runtime notices.
