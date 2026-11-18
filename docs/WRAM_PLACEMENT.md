# UPMEM: cluster placement and MRAM–WRAM residency

Focused literature review, **18 November 2026**. The question is which existing
methods group related data and decide what should stay in fast WRAM rather than
be repeatedly accessed through MRAM. Relevant paper sections and selected
official implementations were inspected; their experiments were not rerun.

**Finding:** DRIM-ANN directly describes hot-data selection for WRAM. UpANNS
describes phase-dependent WRAM reuse in a cluster-based ANN algorithm. PimPam
and PID-Join provide useful graph and database implementations of partitioned
data with explicitly managed local buffers. These establish substantial prior
work, but they are not all algorithms for dynamically caching whole graph
communities.

## The architectural distinction

In the UPMEM generation studied by these papers, each DPU has 64 MiB MRAM and
64 KiB WRAM shared by its tasklets. Stack space, intermediate results, queues,
metadata and transfer buffers all compete for WRAM. It is a software-managed
scratchpad, not an automatically filled hardware data cache.

There are three different decisions:

| Decision | Example |
| --- | --- |
| Form data groups | Group nearby ANN vectors, partition a graph, or hash-partition a join input. |
| Assign groups to DPUs | Place or replicate a cluster in one or more DPUs' MRAM banks. |
| Manage a DPU's working set | Copy selected data into WRAM, retain it while useful, then reuse the space; write modified results back as needed. |

The bulk data normally remains in MRAM while WRAM holds working copies or
intermediate state. A cluster may be too large for WRAM, requiring slices or
blocks. An IVF cluster of vectors, a graph community and a cluster of DPU cores
are different objects. Papers using one meaning do not automatically solve
the others.

## Closest papers and exactly what they decide

### 1. DRIM-ANN — the closest direct residency policy

*DRIM-ANN: An Approximate Nearest Neighbor Search Engine based on Commercial
DRAM-PIMs*, SC 2025.
[Paper inspected: arXiv v2](https://arxiv.org/pdf/2410.15621v2),
[publication DOI](https://doi.org/10.1145/3712285.3759801).

Read **§3.2, Memory Optimizations**, especially PDF page 5. The paper estimates
access counts for data types such as codebooks and centroids using its I/O
model. It defines their heat as **“average access times per bit”** and states
that the hottest data are placed in the WRAM buffer. This is an explicit
reuse-per-capacity criterion for choosing what receives scarce fast memory.

Also read **§3.1**: for a squaring lookup table too large for WRAM, frequently
used entries are stored in WRAM and the remainder in MRAM. This is a concrete
two-level residency decision.

Separately, §3.2 splits ANN clusters into slices, replicates hot clusters and
assigns slices to DPUs to balance work. The slice threshold accounts for
indexing overhead and fitting metadata in WRAM. This must not be described as
an algorithm that moves whole hot clusters into WRAM: its WRAM discussion
selects useful data, while cluster replication concerns distribution across
DPUs. The overview's broad phrase “hot vectors in WRAM” needs this qualification.

**Relevance:** a necessary prior-work comparison for any proposed frequency- or
reuse-based WRAM policy. Simply keeping hot data in WRAM is already published.
This paper concerns cluster-based ANN, not arbitrary graph communities.

### 2. UpANNS — working-set selection through phase lifetimes

*UpANNS: Enhancing Billion-Scale ANNS Efficiency with Real-World PIM
Architecture*, SC 2025.
[Paper inspected: arXiv v2](https://arxiv.org/pdf/2410.23805v2),
[publication DOI](https://doi.org/10.1145/3712285.3759777).

Read **§4.2.1–4.2.2 and Figure 6**, especially PDF page 6. In its SIFT example,
the codebook occupies 32 KiB and the initial lookup table 8 KiB. Once the
codebook is no longer needed, the framework reuses WRAM space for later
processing, including buffers for encoded vectors fetched from MRAM. It
coordinates tasklets within a cluster because concurrent query/cluster
working sets would consume too much shared WRAM.

The selection principle is **data lifetime and processing phase**: preserve
what the next stage needs and reclaim what the previous stage has finished
using. Its separate cluster-placement algorithm uses cluster size and access
frequency to distribute/replicate data across DPUs.

**Relevance:** close prior work for phase-aware memory management, buffer
reuse and the trade-off between tasklet parallelism and buffer capacity. It is
not a general adaptive eviction policy for graph-cluster contents.

### 3. PimPam — the most directly relevant verified graph implementation

*PimPam: Efficient Graph Pattern Matching on Real Processing-in-Memory
Hardware*, SIGMOD/PACMMOD 2024.
[Author-hosted paper](https://people.iiis.tsinghua.edu.cn/~gaomy/pubs/pimpam.sigmod24.pdf),
[DOI](https://doi.org/10.1145/3654964),
[official code](https://github.com/tsinghua-ideal/PimPam/tree/aca09d0bc511de487bbea530812ed11649bb75a0).

Read **§4.2** for subgraph partitioning and **§5, Implementation**, PDF page
15, for local memory management. Necessary subgraphs are stored compactly in
each DPU's MRAM. During set intersection, PimPam manually buffers two input
lists and one result list in WRAM, using **128-byte buffers** in the reported
implementation. It explicitly describes this as manual prefetching and caching.

The [memory declarations and bitmap implementation](https://github.com/tsinghua-ideal/PimPam/blob/aca09d0bc511de487bbea530812ed11649bb75a0/include/dpu_mine.h)
and [set operations](https://github.com/tsinghua-ideal/PimPam/blob/aca09d0bc511de487bbea530812ed11649bb75a0/dpu/set_op.c)
show the MRAM data structures and bounded local buffers.

**Relevance:** a real graph baseline for MRAM→WRAM staging and intersection
working sets. Its partitioning prepares DPU input; the inspected mechanism
does not select whole graph communities for long-term WRAM residency.

### 4. PID-Join — partitioning to make local processing feasible

*Design and Analysis of a Processing-in-DIMM Join Algorithm: A Case Study with
UPMEM DIMMs*, SIGMOD/PACMMOD 2023.
[DOI](https://doi.org/10.1145/3589258),
[official repository](https://github.com/yonsei-hpcp/pid-join/tree/d5daab61dda997fe0cb3b8a099df328a84b6a210).

The publication metadata/abstract and selected source were inspected; the full
paper was not retrieved in this review. The repository's partitioned hash-join
[build kernel](https://github.com/yonsei-hpcp/pid-join/blob/d5daab61dda997fe0cb3b8a099df328a84b6a210/src/dpu/src/join/a2a_srj_build.c)
allocates a **32 KiB WRAM hash-table buffer** and iterates over partitions. Its
[probe kernel](https://github.com/yonsei-hpcp/pid-join/blob/d5daab61dda997fe0cb3b8a099df328a84b6a210/src/dpu/src/join/a2a_srj_probe_inner_mt.c)
similarly uses a bounded local hash-table buffer and partition data in MRAM.

**Relevance:** a database example of grouping data so the current computation
can use a small local working set. This is partition-at-a-time execution, not
evidence of a graph-topology-based hot-cluster retention algorithm. The 32 KiB
figure describes the inspected kernels, not every PID-Join variant.

### 5. ATiM — automatically choosing local-memory tiles

*ATiM: Autotuning Tensor Programs for Processing-in-DRAM*, ISCA 2025.
[Paper inspected: arXiv v3](https://arxiv.org/pdf/2412.19630v3),
[DOI](https://doi.org/10.1145/3695053.3731096).

Read **Figure 3 and its discussion**, PDF page 4, and the compiler design in
§5. ATiM searches tensor schedules, including caching tile sizes and work
distribution. It explicitly examines how different local tiles affect
execution. This is relevant to automatic transfer/buffer-size selection,
although tensor tiles are not irregular graph clusters and the mechanism is
schedule tuning rather than runtime hot-cluster eviction.

### 6. The uPIMulator paper — an architectural comparison, not stock software

*Pathfinding Future PIM Architectures by Demystifying a Commercial PIM
Technology*, HPCA 2024.
[Paper inspected: arXiv v3](https://arxiv.org/pdf/2308.00846v3),
[DOI](https://doi.org/10.1109/HPCA57654.2024.00029).

Read **§V-D and Figures 15–16**, PDF page 12. The authors simulate replacing
the scratchpad-centric design with an on-demand cache architecture, including
8-way caches with LRU replacement. They find workload-dependent trade-offs:
automatic caching can reduce overfetching, while scratchpad management is
better for some other workloads.

**Relevance:** direct background for the residency/overfetching problem.
However, the evaluated cache changes the architecture; it is not an existing
hardware cache on stock UPMEM, nor a software graph-cluster placement policy.

## Related names that can be misleading

- **PyGim:** its “PIM clusters” group processing cores. Its partitioning and
  tuning work is relevant, but that term does not identify data clusters chosen
  for WRAM. See [§3.2 of the paper](https://arxiv.org/pdf/2402.16731v7).
- **PIM-CACHE:** the [2026 preprint](https://arxiv.org/pdf/2603.23762) reduces
  redundant host-to-DPU transfers using content-aware staging/deduplication.
  Its name does not make it a local MRAM–WRAM cluster cache. The abstract and
  staging-design discussion were inspected for this boundary distinction.
- **Turbocharge ANNS / PIMANN:** the [USENIX ATC 2025 paper](https://www.usenix.org/system/files/atc25-wu-puqing.pdf)
  adapts cluster replication as popularity changes (§4.3), adding/removing
  replicas in **MRAM across PUs**. That is relevant adaptive placement, but a
  different decision from which data remain in a DPU's WRAM.

## Implication for the thesis

The most useful reading order is **DRIM-ANN → UpANNS → PimPam**, followed by
PID-Join for a non-graph example and the uPIMulator paper for architectural
limits. SparseP's coarse matrix transfers/fine indirect vector accesses and
SimplePIM's scratchpad accumulators, already listed in
[the broader review](LITERATURE.md), are further local-working-set baselines.

A possible question remains whether graph-related groups or sub-blocks can be
admitted and retained according to changing reuse **after charging for transfers,
metadata, unused bytes and reduced tasklet capacity**. Compare any candidate
against frequency-per-capacity selection, phase-based reuse, fixed streaming
buffers and a feasible software-cache baseline. Grouping data is not by itself
a benefit: one hot member can cause a large, mostly unused cluster to be fetched.

This review does **not** establish that no prior work dynamically selects graph
communities for WRAM. Recent graph-mining systems, including DyPamear and
Prism, also appeared in discovery and need full mechanism checks before a
novelty claim. The supported conclusion is narrower: hot-data residency,
phase reuse, explicit graph buffering and automatic tiling already have close
UPMEM precedents.
