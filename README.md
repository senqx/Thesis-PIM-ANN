# Data reuse for graph aggregation on UPMEM

Master's research by **Artashes Atanesyan**.

**[Read the short thesis (PDF)](thesis/short-thesis.pdf)** ·
[Markdown version](thesis/short-thesis.md) ·
[Research questions](docs/CONTRIBUTION_PLAN.md) ·
[Validation record](docs/VALIDATION.md)

When does keeping graph data in a DPU's small working memory save more time
than it costs to manage? This project investigates that question using
compiled UPMEM programs, reproducible simulations and explicit accounting
for preparation, memory capacity and data movement.

**Status — 23 November 2026:** the exploratory experiments and baseline
controls are complete. A predictive model and selective preparation policy
remain proposed work. The thesis explains both the results and the unresolved
research questions. Hardware speedup, energy savings and end-to-end application
acceleration have not been demonstrated.

## What the experiments show

UPMEM is a near-memory form of processing-in-memory. Each DPU has a large
local DRAM bank (**MRAM**) and a small, software-managed working memory
(**WRAM**). Its hardware threads, called tasklets, share that WRAM.

Our kernel sums the values associated with each graph vertex's neighbors.
It compares ordinary streaming, prepared batches that reuse source values,
and preloading the entire feature table when it fits.

| Finding | Evidence and interpretation |
| --- | --- |
| Fewer reads do not guarantee faster execution. | Early retention policies save traffic but lose to tuned streaming after bookkeeping costs. |
| Prepared batches can beat streaming. | Across five work sizes, the original format reaches about 5% fewer simulated cycles on the larger reusable inputs. Uniform accesses lose. |
| Preparation can consume the kernel saving. | The original Python planner needs roughly one hundred valid uses in the largest positive cases. This is a conditional estimate, not a hardware result. |
| A stronger baseline changes the recommendation. | At 3,072 destinations, shared preloading is 29–30% faster than streaming on the synthetic inputs whose entire 4 KiB feature table fits in WRAM. |
| The strict storage constraint is still unresolved. | Compact dictionaries improve batching, but one sampled real-graph input still exceeds the installation budget. |

The next useful question concerns **working sets larger than available WRAM**:
can selective reuse beat compact streaming and applicable partial residency,
stay within the resource budgets, and repay its preparation? The
[contribution plan](docs/CONTRIBUTION_PLAN.md) defines the three RQs, closest
prior work and evidence still required. Novelty has not been established for
the proposed selector.

## Read in this order

| Document | What it gives you |
| --- | --- |
| [Short thesis](thesis/short-thesis.pdf) | The domain, prior work, RQs, method, results, costs and remaining research direction |
| [Contribution plan](docs/CONTRIBUTION_PLAN.md) | The precise proposed contribution and how to test it |
| [Five-size experiment](experiments/access-plan-fivepoint/README.md) | Original batching curves, CPU preparation timings and replay instructions |
| [Baseline controls](experiments/baseline-gates/README.md) | Compact dictionaries, shared residency and the updated recommendation |
| [Literature review](docs/LITERATURE.md) | Reading links, established techniques and limits of the novelty assessment |
| [Platform setup](docs/PLATFORM.md) | Pinned compiler/simulator, setup commands and timing-model limitations |

Supporting material preserves the [first residency pilot](experiments/wram/README.md),
[prepared-access experiments](experiments/access-plan/README.md),
[three-size checkpoint](experiments/access-plan-scaling/README.md),
[WRAM placement literature](docs/WRAM_PLACEMENT.md), and
[CPU-mediated PIM–GPU feasibility](docs/PIM_GPU.md).
The [original broader proposal](docs/RESEARCH_PLAN.md) is retained for context.

## Check and reproduce the evidence

Run the retained-record audits with Python 3, from the repository root:

```sh
python3 scripts/access_plan_fivepoint.py verify
python3 scripts/access_plan_gates.py verify
```

These commands check hashes, counters, matched work and output records.
After setting up the [pinned Go uPIMulator](docs/PLATFORM.md), freshly execute
representative archived programs:

```sh
python3 scripts/access_plan_fivepoint.py replay
python3 scripts/access_plan_gates.py replay
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

## Scope and provenance

The main study uses one simulated DPU, twelve tasklets, 8-byte integer records,
two seeds per input family and one sampled real graph. It is an aggregation
kernel, not complete GNN training. The Go simulator's timing for these kernels
has not been validated against hardware. GPU integration and energy evaluation
remain outside the completed work.

The repository name is historical. The earlier HNSW/DRAM-service thesis and
its evidence remain in the
[archived revision](https://github.com/senqx/Thesis-PIM-ANN/tree/fcab5d2be844dd1097f7f0ae13bbe500a12f8caf).
[Previous results](docs/PREVIOUS_RESULTS.md) gives a concise summary and recovery
instructions. Dependencies and regenerable runs live in ignored directories.

## License

[MIT](LICENCE). Third-party software and datasets retain their own terms;
the experiment artifacts include attribution and runtime notices.
