# Is there a useful PIM–GPU division of work?

Literature and feasibility assessment, 23 November 2026. No GPU–PIM experiment
has been performed in this project.

**Yes, but the useful case is narrower than “PIM gathers data for the GPU.”**
The strongest case is persistent, large data in PIM memory, with near-memory
work that reduces or filters the data before the GPU receives it. GPU matrix
operations can then consume the smaller result. Whether this beats a CPU
doing the same preprocessing is an experimental question.

## What would actually change?

A GNN (graph neural network) learns representations of nodes using their
neighbors. A layer often gathers neighbor feature vectors, combines them, and
applies a learned transformation. Gathering and combining can be dominated
by scattered reads; the learned transformation can use efficient GPU matrix
kernels. Not every GNN permits the same operation order or a simple sum.

For an illustrative sum aggregation, reading 32 vectors of 128 FP32 values
requires 16 KiB of feature input; their sum is one 512-byte vector. This is a
32:1 reduction in **logical feature payload**, before accounting for indices,
partitioned partial results, replication or transfers. It is not a measured
speedup. With UPMEM, FP32 arithmetic is software-emulated, which can erase the
advantage. Our current DPU pilot uses integer addition and cannot establish
FP32 performance or model accuracy.

A good CPU–GPU baseline can also sum the vectors before sending them to the
GPU. Against that baseline the GPU receives the same 512 bytes. PIM's potential
benefit is then its near-memory execution and aggregate memory bandwidth,
**not another reduction in PCIe traffic**. Pure gathering may have a throughput
benefit in some systems, but provides no inherent reduction in output volume.

For the stock host-attached UPMEM system considered here, the practical path is:

```text
requests/indices from CPU
        ↓
DPU: read resident MRAM data → aggregate/filter using WRAM
        ↓
CPU memory: receive partial results and merge if needed
        ↓
GPU: dense computations on the resulting batch
```

There is no assumed direct DPU→GPU transfer primitive. Host staging, launching
DPUs, merging partial sums and synchronization must be charged. This is
different from a custom PIM design inside GPU-attached high-bandwidth memory.
Those architectures have different connectivity and resource constraints.

## Closest evidence inspected

| Work | What it establishes | Limit on our interpretation |
| --- | --- | --- |
| [UpDLRM, DAC 2024](https://arxiv.org/pdf/2406.13941v2), [DOI](https://doi.org/10.1145/3649329.3658266) | Real UPMEM embedding lookup/reduction; partitions tables and caches selected partial sums. §4 compares with CPU-only and CPU–GPU implementations. | Its conclusion leaves a DPU–GPU system as future work. The GPU-resident hot-vector cache described in §4.1 belongs to its **FAE baseline**, not UpDLRM. Its partial-sum cache is in **MRAM**, not an adaptive WRAM cache. |
| [PyGim, inspected v7](https://arxiv.org/pdf/2402.16731v7) | Separates GNN aggregation on PIM from combination on the host; tunes partitioning and parallelism. Includes CPU–PIM execution and a training appendix. | §4 says the available evaluation platform is CPU–PIM; GPU–PIM support is a design capability, not a measured deployment. §4.8 and Appendix A.6 report GPU comparisons in which GPUs are substantially faster. Greater hardware utilization does not imply lower latency. |
| [RecNMP, ISCA 2020](https://arxiv.org/pdf/1912.12953) | Near-memory embedding reduction, table-aware scheduling and batch-informed caching. | A proposed hardware architecture, not stock UPMEM software. Batch reuse hints and pooling near memory are already established ideas. |

These papers establish close prior art. This focused review is not a proof
that no later paper solves a particular hybrid scheduling problem.

## When should we consider it?

| Workload condition | Assessment for our UPMEM target |
| --- | --- |
| Large, mostly read-only embedding tables; simple pooling; many requests amortize initial placement | Plausible application, already studied in related systems. |
| Graph aggregation with enough reuse and modest arithmetic cost | Relevant to our WRAM study; host exchange and representation costs remain unresolved. |
| Dense layers whose weights and activations already fit GPU memory | Weak initial target: moving work away from optimized GPU kernels adds costs. |
| Frequently updated features or embedding weights during training | Harder: update traffic, ownership and consistency can remove the benefit of keeping data resident in PIM. |
| PIM only gathers the same bytes for the GPU | Needs evidence against optimized CPU gathering; copying alone is not a contribution. |

A first latency model must compare equivalent work:

```text
CPU–GPU: CPU gather/reduce + host→GPU transfer + GPU work
PIM–GPU: dispatch + DPU gather/reduce + DPU→host transfer
         + host merge + host→GPU transfer + GPU work
```

Add preprocessing and initial placement divided by the number of batches that
reuse them. For a steady-state pipeline, measure stage overlap and contention;
adding all stages predicts unoverlapped latency, not overlapped throughput.
Compare with GPU-resident execution when it fits, and with a capacity-matched
CPU–GPU streaming/caching baseline when it does not. Account for total memory,
both transfer directions, equal precision and equivalent outputs.

## Implication for this thesis

Keep the [three WRAM-reuse questions](CONTRIBUTION_PLAN.md) as the core investigation. A successful
residency policy could support the sparse preprocessing stage of a hybrid
pipeline, but it would not by itself prove a faster hybrid application.

A later, bounded extension could ask: **when does improved local retention
make host-mediated PIM aggregation competitive with tuned CPU aggregation
before an unchanged GPU stage?** First establish a benefit in complete DPU
execution under a traffic limit; then measure the transfer and merge costs.
We currently have neither an integrated GPU–UPMEM platform nor a validated
joint simulator, so a numerical end-to-end speedup would be speculative.

The broad idea of splitting sparse and dense work across PIM and conventional
processors is established. Any contribution here would need to be a specific
policy, a defensible break-even characterization, or a useful negative result.
