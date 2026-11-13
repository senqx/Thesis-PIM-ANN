# Adaptive data movement for irregular workloads on UPMEM

Master's research by **Artashes Atanesyan**. The repository name is historical.

**Status: research reset and feasibility review, 13 November 2026.** There are
no experimental results for the new hypothesis yet. The previous DRAM-service
study is preserved in Git; it is not evidence for this new project.

## The problem

Many programs spend substantial time waiting for data. Graph traversal, sparse
matrix operations and indexed lookups are especially difficult: the address of
the next item often depends on an item just read. Moving computation close to
memory can reduce some transfers, but it does not remove this dependency or
make communication free.

This project asks whether a small adaptive policy can decide **what to fetch,
how much to fetch, and when to fetch it**, while respecting traffic and memory
budgets. Fetching early is useful only if the data is needed and the transfer
cost can be hidden or reduced. Doing nothing must remain a valid decision.

## Objective and hypothesis

**Objective:** design and evaluate adaptive data movement and prefetching for
irregular workloads on a heterogeneous host–DPU system, starting with UPMEM.
Evaluate execution time together with communication volume, buffer use and
implementation overhead. Assess energy only with a justified model or hardware
measurements.

**Hypothesis to test:** information about workload structure and recent access
behaviour can improve execution time over tuned static and conventional
feedback policies **under the same traffic and memory limits**. The experiments
may reject this hypothesis.

The initial target has a CPU host and identical DRAM Processing Units (DPUs).
Different DPU capabilities are an optional later extension. There is currently
no hardware or installed UPMEM SDK. A pinned copy of **uPIMulator** has been
obtained; [platform status and setup](docs/PLATFORM.md) distinguish the working
build checks from the unresolved compiler dependency.

## Read in this order

| Document | Purpose |
| --- | --- |
| [Literature and possible contribution](docs/LITERATURE.md) | Domain foundations, established work, candidate gaps and limits of this review |
| [Research plan](docs/RESEARCH_PLAN.md) | The five RQs, falsifiable hypothesis, baselines, resource budgets and scope decisions |
| [Platform status](docs/PLATFORM.md) | Pinned simulator, reproducible acquisition and what it can currently support |
| [Previous results](docs/PREVIOUS_RESULTS.md) | Concise historical findings and recovery instructions |

## Scope

Start by testing a reusable mechanism for **irregular accesses whose upcoming
addresses become available through an index array or worklist**. Use controlled
access patterns, sparse operations and graph traversal to discover where it
works. Narrow to graphs or one traversal phase only if the evidence requires
it. Broad usefulness must be demonstrated across workloads.

The first task is a functioning, understood execution platform. The second is
to establish whether there is enough opportunity beyond strong fixed policies.
A new predictor or framework comes after those checks.

## Historical artifact

The completed earlier thesis, code and retained evidence remain at
[`archive/dram-service-2026-11-13`](https://github.com/senqx/Thesis-PIM-ANN/tree/fcab5d2be844dd1097f7f0ae13bbe500a12f8caf).
Its active sources, PDFs, results, workflows and build caches have been removed
from this branch. Git history remains recoverable. Simulator dependencies live
in ignored `.deps/`; they are not vendored into the research repository.

## License

[MIT](LICENCE). Third-party dependencies retain their own licenses.
