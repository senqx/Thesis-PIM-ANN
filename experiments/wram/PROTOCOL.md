# Exploratory MRAM–WRAM residency study

Protocol started 23 November 2026, before new execution results. This is a
bounded feasibility and mechanism study, not a final confirmatory campaign.
The earlier Python traffic pilot is exploratory motivation, not DPU evidence.

## Questions

1. Do graph-derived signals improve residency beyond inexpensive access history?
2. When should a contiguous group be fetched/retained whole versus in subblocks?
3. When should WRAM be reassigned from retention to streaming input buffers?

Use a read-only graph-neighbor feature gather/reduction as the initial kernel.
Keep the graph, vertex order, arithmetic and logical output identical within
each comparison. GNN training and mutable gradient caches are outside this
study. A graph neural network (GNN) combines neighboring nodes' features and
then applies learned transformations; our kernel addresses only the former.

## Execution and decision boundaries

First compile and simulate an upstream vector-addition smoke test with checked
output. Then execute actual compiled DPU policy code with reference outputs.
Record simulator and compiler versions and all integration patches. Kernel
cycles include policy bookkeeping, initialization, transfers and computation.
Report host preprocessing separately; do not label kernel time end-to-end ANN
or ML latency. No energy claim without a validated energy model.

Begin with single-DPU cases and a limited tasklet sweep. All methods receive
the same maximum WRAM allowance, with metadata, stacks and buffers included.
Static methods may use less space. Count reads and writes separately, including
unused prefetched bytes. Pin graph-derived metadata and its preparation cost.
Keep arithmetic integer and identical so arithmetic precision is not a hidden
variable; this does not demonstrate floating-point GNN performance.

## Baselines and ablations

- Direct row fetching with batched index reads; sweep legal fixed buffer sizes.
- Inexpensive history-only retention (direct-mapped or low-associativity cache).
- Degree/frequency-based static pinning, paying membership and fill costs.
- Graph-hinted admission paired with an otherwise identical history policy.
- Coarse group transfer versus selective block transfer.
- Fixed WRAM partitions versus a lightweight phase decision with real cost.

Retain tuned fixed configurations and simple alternatives. A graph policy
that only beats unbuffered scalar loads has not established its contribution.
Do not assume community membership is freely available or that a community
fits WRAM. Generated communities are diagnostic information; use real graphs
before claiming general applicability. Include shuffled processing order as a
control, without changing input or output mathematics.

## Workloads, metrics and limits

Explore controlled local/community, uniform and phase-changing cases, plus
small public graph inputs if platform throughput permits. Separate calibration
from evaluation inputs/seeds. Start with a small matrix and expand to resolve
specific observed uncertainties; document every scope reduction and failed run.

Primary metrics: complete simulated DPU kernel cycles and local MRAM bytes.
Report absolute and paired relative differences. Also record transfer counts,
instructions, WRAM occupancy, output checks, preprocessing and metadata size.
Primary traffic acceptance: no extra bytes over the strongest relevant baseline;
also disclose latency/traffic trade-offs up to 10% additional bytes. Savings
under 5% are exploratory mechanism evidence, not a deployment recommendation.
These are investigation criteria, not physical hardware error bounds.

Do not interpret deterministic reruns as independent statistical samples. Do
not optimize on evaluation outcomes and later call them untouched. Synthetic
and single-DPU conclusions remain scoped accordingly. Negative outcomes are
retained, including cases where simpler policies win or adaptation does not
repay its cost.

## First executable pilot: scope decisions

The first matrix uses 128 source vertices, 64 destination vertices and eight
sampled neighbors per destination (sampling with replacement), with 64-byte
integer feature rows. It is a synthetic bipartite aggregation workload, not a
complete real GNN graph or traversal engine. Two seeds, five graph/order
conditions, eight policies and one/four tasklets produce 160 configurations.
Community and shuffled cases share the underlying graph: there are eight
graph instances and ten graph/order conditions, not 160 independent samples.

All cases are exploratory. This initial matrix does not fit a learned policy
or reserve a confirmatory split. The adaptive probe threshold is fixed in C
before execution; results must not be used to silently replace it. Static
pinning and degree admission use source in-degree over the complete known
input graph. For this full pass, degree equals reference frequency. Obtaining
that information is charged as metadata reads and initialization inside the
DPU; host graph preprocessing remains outside kernel timing.

The two streaming settings use maximum index transfers of 128 and 2048 bytes.
This is a limited buffer comparison, not exhaustive tuning. All variants
reserve the same 3328-byte workspace/tasklet, including metadata even when
unused, and the upstream linker's 24 reserved 2048-byte stacks. The one- and
four-tasklet programs fit 64 KiB; this does not characterize an optimized
11–16-tasklet allocation. Fixed feature-cache capacity is 2048 bytes/tasklet.

The adaptive prototype probes 32 references per 256-reference window and
retains data if at least four probe references hit. Otherwise it bypasses
retention and expands the index buffer. In the four-tasklet cases each tasklet
has only 128 references, so this is a short-window bypass check; it does not
exercise a full 256-reference cycle or the larger overlapping allocation.

Real graph inputs, additional feature sizes, fully occupied tasklet schedules,
larger WRAM allocation sweeps and hardware timing validation are not completed
by this pilot. Its purpose is to identify whether these simple mechanisms have
enough promise to justify that next step. It cannot settle the broad hypothesis
or establish a publication-level new algorithm.
