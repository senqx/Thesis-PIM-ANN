# Data Reuse for Graph Aggregation on UPMEM

**Artashes Atanesyan**  
Master's research — experimental study and research direction, 23 November 2026

## Abstract

On UPMEM, processors beside DRAM banks explicitly move data into a small
working memory. Reusing that data can avoid reads, but its management can
consume the time saved. This exploratory study evaluates prepared batches
for repeated graph aggregation against streaming and shared-memory residency.
A five-size experiment finds about 5% fewer simulated kernel cycles on larger
reusable worklists, with roughly one hundred invocations needed to repay the
reference planner. Additional controls change the recommendation: compact
dictionaries improve batching, but preloading the entire feature table is
29–30% faster than streaming where the table fits in working memory. Batching
loses on uniform accesses and does not consistently meet the index-storage
budget. The resulting evidence narrows the research opportunity to working
sets larger than available working memory. A predictive, budget-constrained
selector remains proposed work. The study supplies reproducible baselines
and failure cases; it establishes neither a novel general algorithm nor
hardware, energy or end-to-end application gains.

## 1. The problem: moving less data must also mean doing less work

The **memory wall** describes a familiar systems problem: a processor can
perform arithmetic faster than useful data can reach it. Graph algorithms
make this difficult because neighboring vertices may be scattered in memory.
A program may spend more effort finding and moving their values than adding
them together.

Processing-in-memory (PIM) moves computation closer to stored data. UPMEM
implements **processing near memory (PNM)**, a programmable form of PIM:
small processors called
**DRAM Processing Units (DPUs)** operate beside DRAM banks. Each DPU has a
64 MiB main memory, **MRAM**, and a 64 KiB working memory, **WRAM**. Up to 24
hardware threads, called tasklets, share that working memory. The CPU launches
work and coordinates the system [1].

Think of MRAM as a large storeroom and WRAM as a small workbench. A DPU must
explicitly bring records to its workbench before using them. Keeping a record
there can avoid another trip. However, checking what is already present,
choosing replacements and maintaining metadata also takes instructions.
The right question is therefore whether saved transfers exceed **all the work
needed to save them**.

Our workload is **graph aggregation**: for each destination vertex, read the
values associated with its neighbors and sum them. A **graph neural network
(GNN)** uses information from neighboring nodes to learn a representation of
each node. Aggregation is one stage of that process; a later transformation
applies learned parameters. This study isolates integer aggregation. It does
not train a GNN or evaluate floating-point model accuracy.

Our baseline, **streaming**, reads neighbor IDs in chunks and fetches each
requested value on demand. Those values may still be scattered in memory.
The **working set** is the collection of values needed by a computation.
Whether that set fits in WRAM turns out to be central to the choice of method.

## 2. Existing work and the questions we investigate

UPMEM optimization already has substantial prior work. PrIM characterizes
the real machine and its data-transfer costs [1]. SparseP develops efficient
sparse matrix kernels, including chunked metadata access and indirect vector
reads [2]. PyGim studies graph aggregation, partitioning and cooperative
processor–PIM execution [3]. ATiM tunes tensor schedules and local-memory
tiles [4]. UPMEM Unleashed shows how compiler and instruction costs can limit
performance [5]. SparseP also discusses amortizing matrix installation over
repeated operations; setup amortization is already an established idea.

PIM-CACHE [6] is especially close at the representation level: it stores
distinct blocks and ordered offsets to reduce CPU-to-MRAM transfers. Our
batches reduce MRAM-to-WRAM reads of repeated source IDs and can retain their
access metadata when feature values change. That difference identifies the
comparison to make; it does not establish priority. Recent work also covers
PIM cost modelling [7] and the useful lifetime of prepared sparse schedules
[8]. These 2026 papers are cited as preprints.

Caching, batching, compressed indices and preparing execution decisions in
advance are established ideas. This thesis does not claim to invent them.
The completed contribution is an implemented experimental artifact and a
controlled comparison of **execution cost, preparation cost and memory traffic**
on the selected UPMEM model. The streaming baselines follow
established access principles; they are not reproductions of the complete
SparseP or PyGim systems.

Three research questions define the direction:

- **RQ1 — Predict the benefit:** Which observable access and resource
  characteristics predict whether WRAM reuse reduces complete execution time,
  beyond simply counting saved reads?
- **RQ2 — Respect the budget:** Can selectively preparing reusable regions
  improve execution without increasing installed index bytes or local reads,
  while fitting the same WRAM limit?
- **RQ3 — Repay preparation:** How many valid uses are needed to repay
  inspection, preparation and installation, and can short-lived work be
  correctly rejected?

The hypothesis is conditional: selective preparation can improve total cost
for known, repeatedly used access sequences under those resource limits.
The completed experiments establish baselines and partial answers. A predictive
model and selective planner have not been implemented. The narrative therefore
proceeds from a simple mechanism, through its costs and stronger controls, to
the narrower problem that remains open.

## 3. The idea: prepare the references, load current values, preserve the sum

Earlier exploratory kernels in this project showed that runtime retention
can save reads and still lose on total cycles. Moving individual cache
decisions into a prepared per-reference plan reduced some lookup instructions,
but did not beat streaming in the initial small workloads. This motivated a
simpler inner loop: prepare an entire small batch, load its unique records,
then aggregate without a cache lookup for every reference.

Suppose a batch requests source IDs `7, 12, 7, 4`. Its unique-record list is
`7, 12, 4`, and its slot list is `0, 1, 0, 2`. The DPU reads three records
instead of four, then follows the slot list. The value for source 7 is still
added twice. Removing duplicate **loads** does not remove repeated terms
from the mathematical operation.

![Prepared batches preserve the requested arithmetic while reusing loaded values.](figures/method.png)

*Figure 1. The CPU prepares addresses and slots. The DPU loads current values
and preserves the original reference order and multiplicity.*

Each tasklet receives its own batches and a 512-byte retained-payload buffer.
The tested windows contain 16, 32 or 64 references. With 8-byte records, the
largest window fits even when every requested record is different. A header,
unique source IDs and byte-sized slot codes describe each batch. Their
traffic, padding and storage are included in the measurements.
The original format uses 32-bit dictionary IDs. Section 7 tests 16-bit IDs
and shared residency as stronger controls.

Only access metadata survive between invocations. Every invocation loads
fresh feature values, so values may change without reusing stale WRAM contents.
Topology, processing order, tasklet assignment and record width must remain
compatible with the plan. A changed traversal frontier may invalidate it.
This is explicit batching and reuse, not prediction of undiscovered neighbors
or an assumed asynchronous prefetch facility.

## 4. Evaluation: equal work and explicit accounting

The evaluation uses the pinned Go implementation of uPIMulator [9] with an
archived UPMEM SDK 2023.1.0 compiler. It executes compiled DPU instructions and
counts complete kernel cycles at a modelled 350 MHz. The simulation includes
bookkeeping and arithmetic as well as memory requests. No timing parameters
were modified to favor the candidate. There is no UPMEM hardware in this study.

| Experimental choice | Setting |
| --- | --- |
| Work per invocation | 192, 384, 768, 1,536 or 3,072 destinations; eight references each |
| DPU resources | One DPU; twelve tasklets; 8-byte records; shared 64 KiB WRAM limit |
| Prepared method | 16-, 32- and 64-reference windows; 512-byte retained payload per tasklet |
| Streaming controls | 16-bit source IDs; 128-, 256- and 1,024-byte index buffers |
| Paired inputs | Three families; two seeds per size; identical inputs and arithmetic across policies |
| Preparation timing | Python reference encoder; one warm-up and eleven timed constructions per distinct encoder/input |

*Table 1. Evaluation settings shared by the paired comparisons.*

Community inputs choose 90% of references from a local 16-source group;
uniform inputs choose from the full 512-source universe. The third family
samples neighborhoods from the public SNAP ca-GrQc collaboration graph [10].
It selects distinct destinations, then samples eight neighbors **with
replacement** per destination. This is sampled aggregation, not a complete
pass over the real graph. Different sizes need not use nested samples.
Increasing the number of destinations increases work per invocation, while
the synthetic source table remains 512 records, or 4 KiB. This experiment
does not sweep the working-set capacity.

Every comparison uses the fastest tested streaming buffer for that same
input. This is a strong hindsight comparator, not a deployed selector.
The 16-bit indices are valid for all tested source IDs. All programs fit
WRAM, including the linker's reserved stacks; total reservations range from
52,128 to 62,880 bytes. Equal limits do not require identical allocations.

We verify every output value against a reference sum, interpret each plan
independently and check exact MRAM read/write counts. Reads include headers,
dictionaries, slot codes and feature records. Installed metadata also include
unread tasklet-segment padding. Logical inputs and outputs must match across
policies. Kernel cycles include startup, loads, bookkeeping, arithmetic and
final stores; host preparation is measured separately.

The five-size grid has 180 configurations. It preserves 108 earlier DPU
records and adds 72 executions at the two intermediate sizes. All five sizes
receive a new preparation campaign with 1,320 timing samples. The study is
exploratory: design and baseline improvements preceded this extension.
Configuration counts are not counts of independent statistical experiments.
We report descriptive paired means and both seeds, without significance claims.
The later baseline screen adds 14 executions and reuses 24 records from that
grid: 194 distinct configurations across these two artifacts. The 24 reused
records must not be counted twice. Earlier exploratory pilots remain separate.

## 5. Results: the method helps only in part of the design space

Figure 2 and Table 2 show the original 64-reference batches with 32-bit
dictionary IDs. Each curve has five actual size points. Negative changes mean
fewer cycles or bytes. Section 7 explains why these streaming comparisons
alone do not identify the best use of WRAM.

![Five workload sizes show the interaction between execution cost and read savings.](figures/performance.png)

*Figure 2. Original batch format: complete simulated kernel cycles and local MRAM reads relative to
the best tested streaming buffer. Points are means of two paired changes;
shading spans the two seeds, not a confidence interval. Output writes are
identical. Lines connect tested points and do not prove intervening behavior.*

<!-- begin:cycle-table -->
| Destinations | Community | Sampled ca-GrQc | Uniform |
| ---: | ---: | ---: | ---: |
| 192 | +1.44% | +5.38% | +53.82% |
| 384 | +1.09% | +1.97% | +51.21% |
| 768 | −3.04% | −0.60% | +50.71% |
| 1,536 | −4.74% | −4.07% | +49.22% |
| 3,072 | −5.35% | −5.05% | +49.26% |
<!-- end:cycle-table -->

*Table 2. Original batch64: mean paired change in complete simulated DPU cycles.*

The method reduces both cycles and local reads on the larger
community and sampled-graph worklists. At 3,072 destinations, local reads fall
by 47.80% and 40.77%, respectively. The community kernel saves a mean 27,732
cycles, or 79.23 microseconds at the model clock. Saving nearly half the reads
produces only about 5% fewer cycles: transfer count is not a substitute for
complete execution measurement.

Uniform access fails both tests. Its largest case is 49.26% slower and reads
24.60% more bytes. There is too little reuse to repay batch metadata and
execution overhead. This negative result is part of the practical outcome.

The intermediate points support a size-dependent benefit. At 384
destinations, batch64 still loses on both reusable input families. At 1,536,
it improves their cycle counts by 4.74% and 4.07%. The largest tested size
performs best for those families, but the experiment does not locate a global
optimum. Five points make the observed trend clearer; they do not establish
what happens beyond the measured range.

Window size matters. At 3,072 destinations, community batch16 and batch32 are
29.92% and 10.68% slower than streaming; batch64 is 5.35% faster. Wider batches
reduce repeated headers and expose reuse. The size sweep also changes work
assignment, imbalance and MRAM placement, so it neither isolates startup
amortization nor establishes an optimum beyond the tested range.

## 6. Preparation determines whether the kernel gain is useful

This section accounts for the original batch format in the five-size study;
its payback estimates do not apply to the later compact or shared-residency
controls. The plan is built on the CPU. We time allocation
and encoding into the final metadata byte string. Graph generation, common
feature creation, disk I/O and correctness validation are outside this timer.
The host is an AMD EPYC 7302 running Python 3.13.0; it is not an exclusive
benchmark machine. Policy order is shuffled, and no simulator jobs from this
experiment run during the preparation measurements.

![Preparation and reuse costs distinguish a faster kernel from a worthwhile method.](figures/costs.png)

*Figure 3. Left: batch64 CPU preparation over five sizes, using means of
per-input timing medians. Right: five modelled
reuse counts at 3,072 destinations, combining measured preparation and
simulated kernel time. Extra installation and common system costs are omitted.
The right axis uses a symmetric logarithmic scale outside ±10% to show both
large one-use penalties and small eventual gains. Shading spans the two seeds.*

Preparation grows approximately with work in this range. For community
batch64 it rises from 0.447 ms at 192 destinations to 7.425 ms at 3,072.
That is about 16.6 times the preparation for 16 times the work. Increasing
problem size therefore does not make preparation disappear.

The decision depends on the number of valid uses before rebuilding. Let
`P` be CPU preparation time, `M` installed metadata bytes, `D` kernel time,
`B` effective host-to-DPU bandwidth and `R` the valid reuse count. The serial
accounting is:

```text
planned total − streaming total
  = (P_plan − P_stream) + (M_plan − M_stream)/B
    + R × (D_plan − D_stream)
```

A negative value favors the plan. Equal feature transfers, launches and
output handling cancel only under the stated equal-work assumptions. Transfer
setup differences, contention and overlap remain unmeasured. This is a
conditional cost model, not an observed end-to-end speedup.

At 3,072 community destinations, preparation costs 7.061 ms more
than streaming-index encoding, while the kernel saves about 79 microseconds
per invocation. The two inputs repay preparation after 89 and 91 uses when
extra installation is omitted. Sampled ca-GrQc needs 72–99 uses. These are
estimates from timing medians, not confidence bounds; an optimized native
planner could change them substantially.

For the community case, 100 uses produce only a 0.58% mean reduction in
accounted total time, rising to 4.88% at 1,000 uses. One use is about 379%
slower. If the graph or work assignment changes every invocation, this
implementation is inappropriate. Uniform inputs never repay preparation,
because their recurring kernel cost is also higher.

Local traffic savings have another cost. Community batch64 installs 26.76–29.10%
more metadata than compressed indices; sampled ca-GrQc installs 40.23–42.38%
more. Assuming an effective installation rate of 0.1 GB/s moves their
break-even ranges to 90–92 and 74–102 uses. This rate is a sensitivity
assumption, not a measured UPMEM bandwidth. A strict zero-extra-host-setup
budget rejects the method even when its local-read budget is satisfied.

## 7. Stronger controls change the recommendation

Two baseline checks follow naturally from those results. First, the batch
dictionary should receive the same 16-bit ID compression as streaming.
Second, a 4 KiB feature table may fit entirely in shared WRAM. In that case,
loading it once per invocation could be simpler than managing private batches.

The follow-up tests 3,072 destinations and the same two seeds. Six executions
use compact dictionaries across the three input families. Eight test shared
preloading on the two synthetic families, with 128- or 512-byte index buffers
per tasklet. Cooperating tasklets perform eight disjoint 512-byte loads, then
synchronize before aggregation. The kernel timer includes those costs.

<!-- begin:control-table -->
| Input | Control | Cycles | Local reads | Indices |
| --- | --- | ---: | ---: | ---: |
| Community | Compact batch | −6.18% | −54.43% | −6.25% |
| Community | Shared preload | −29.10% | −78.33% | +0.00% |
| Sampled ca-GrQc | Compact batch | −6.10% | −48.56% | +0.49% |
| Uniform | Compact batch | +41.31% | +5.94% | +54.00% |
| Uniform | Shared preload | −29.63% | −78.33% | +0.00% |
<!-- end:control-table -->

*Table 3. Later controls at one workload size: mean paired changes against
the fastest retained streaming buffer. “Indices” includes installed plan
metadata and padding. Both seeds and both preload buffers are in the artifact;
this table shows the faster tested preload buffer, 128 bytes.*

Shared preloading takes 367,193 cycles on each synthetic input, saving roughly
29–30% relative to streaming. It uses 56,256 bytes of total WRAM, including
stacks, private buffers and synchronization state. Compact batches use 59,904
bytes. Thus full residency wins while using less WRAM than batching in these
cases. The result is a conventional baseline improvement, not a new algorithm.

Full residency is infeasible for the sampled graph in this build: its 41,928-byte
feature table and the linker's fixed 49,152-byte stack reservation already
exceed 64 KiB. Compact batching saves 6.10% of cycles there, but its mean
metadata increase of 0.49% hides a violation on one input: seed 23 grows by
1.17%, while seed 61 shrinks by 0.20%. A per-input storage limit cannot be
satisfied by averaging away violations. Partial residency remains untested.

These are single-size controls, so they support neither a five-point trend
nor a preparation-payback claim for the improved kernels. Changing the index
format also moves feature data in MRAM; its cycle effect is a complete
implementation comparison rather than an isolated decoding measurement.

## 8. What we learned and what remains open

**RQ1 has diagnostic evidence, but no validated predictor.** Work size,
batch width, access reuse and whether the working set fits WRAM all affect the
choice. Fewer reads do not reliably predict fewer cycles. The practical next
step is to test a simple cost model against a reuse-only rule and a well-chosen
fixed policy on unseen inputs.

**RQ2 remains open for selective preparation.** Full shared residency is the
strongest tested choice for the small feature tables. Compact fixed batching
helps some larger working sets, but fails the storage constraint on one sampled
graph input and loses on uniform access. A proposed selector should therefore
target working sets larger than available WRAM and compare with partial/static
residency. Its representation must pay for headers, mode tags and all padding.

**RQ3 has implementation-specific estimates.** The original planner requires
roughly one hundred valid uses in the largest positive cases. This estimate
combines measured Python preparation with simulated kernel time. Comparable
native encoders and explicit inspection costs are needed before treating it
as a practical admission rule for the improved representation.

The proposed contribution is a resource-constrained selection method with
tested applicability conditions. Its novelty still requires a mechanism-level
comparison with the closest work; a new parameter setting or a fallback rule
alone is insufficient. The completed artifact supplies evidence and strong
controls for that next step.

Several limits prevent a broader conclusion. Hardware timing for this Go
uPIMulator build is unvalidated. Published simulator accuracy results concern
another implementation and cannot be treated as our error bars. Two seeds
and one sampled real graph do not establish generality. Features are small
integers; floating-point GNNs, changing frontiers, multi-DPU communication
and energy require separate evidence. A five-percent model gain is a reason
to investigate those costs, not proof of practical hardware acceleration.

A future PIM–GPU application could send DPU aggregation results through the
CPU to a GPU. It would need to include host staging, merging and GPU work and
compare against CPU aggregation and GPU-resident execution. No such hybrid
experiment is claimed here.

## 9. Conclusion

The evidence supports a practical order of decisions: first check whether the
working set can reside in WRAM, then compare compact streaming with more
selective reuse, and finally account for the lifetime needed to repay setup.
The initial five-size result establishes a conditional batching advantage over
streaming. Stronger controls show why that is not enough: ordinary shared
residency is substantially faster where the full feature table fits.

For RQ1, the study identifies relevant costs but does not validate a predictor.
For RQ2, the stricter budget-constrained selective method remains unimplemented.
For RQ3, the original implementation has a measured preparation cost and a
conditional payback estimate; the improved controls still need that accounting.
The next research problem is therefore narrow and testable: determine whether
selective reuse earns its complete cost beyond strong baselines when the
working set exceeds WRAM. The present study provides its reproducible foundation.

## Reproducibility

The [five-point artifact](../experiments/access-plan-fivepoint/README.md)
contains the protocol, all configurations, raw CPU timings, paired comparisons
and exact linked programs with input/output data. Earlier pilots remain
separately preserved. The simulator is pinned to commit
`870d916334e9ff0b190f555f951a9ec3c4257781`. Run
`python3 scripts/access_plan_fivepoint.py verify` for the artifact audit and
`python3 scripts/access_plan_fivepoint.py replay` for four fresh representative
replays. The [baseline-control artifact](../experiments/baseline-gates/README.md)
preserves the 14 new executions and 24 reused comparators. Its verifier and
two representative fresh replays use `python3 scripts/access_plan_gates.py
verify` and `python3 scripts/access_plan_gates.py replay`, respectively. Setup
and full instructions accompany each artifact.

Figures are generated from the retained CSV files. Every data series contains
five points; modelled plan reuse is distinguished from measured CPU preparation
and simulated DPU execution. The later single-size controls are a table, not
an inferred curve. The PDF and its source are built together using
the [document instructions](README.md).

## References

[1] J. Gómez-Luna et al., “Benchmarking a New Paradigm: Experimental Analysis
and Characterization of a Real Processing-in-Memory System,” *IEEE Access*,
vol. 10, pp. 52565–52608, 2022. [doi:10.1109/ACCESS.2022.3174101](https://doi.org/10.1109/ACCESS.2022.3174101).

[2] C. Giannoula et al., “SparseP: Towards Efficient Sparse Matrix Vector
Multiplication on Real Processing-In-Memory Architectures,” *Proceedings of
the ACM on Measurement and Analysis of Computing Systems*, vol. 6, no. 1,
pp. 1–49, 2022. [doi:10.1145/3508041](https://doi.org/10.1145/3508041).

[3] C. Giannoula et al., “PyGim: An Efficient Graph Neural Network Library for
Real Processing-In-Memory Architectures,” *Proceedings of the ACM on Measurement
and Analysis of Computing Systems*, vol. 8, no. 3, pp. 1–36, 2024; presented
at SIGMETRICS 2025. [doi:10.1145/3700434](https://doi.org/10.1145/3700434).
The inspected manuscript is [arXiv:2402.16731v7](https://arxiv.org/abs/2402.16731v7).

[4] Y. Shin, D. Kang and H. Sung, “ATiM: Autotuning Tensor Programs for
Processing-in-DRAM,” *ISCA*, 2025.
[doi:10.1145/3695053.3731096](https://doi.org/10.1145/3695053.3731096).

[5] K. Chmielewski et al., “UPMEM Unleashed: Software Secrets for Speed,”
arXiv preprint, 2025. [arXiv:2510.15927v1](https://arxiv.org/abs/2510.15927v1).

[6] P. Yuhala, M. Mwaisela, P. Felber and V. Schiavoni, “PIM-CACHE:
High-Efficiency Content-Aware Copy for Processing-In-Memory,” arXiv preprint,
2026. [arXiv:2603.23762v2](https://arxiv.org/abs/2603.23762v2).

[7] H. Geng et al., “VIPER: Architecture-Aware Performance Modeling for
Processing-in-Memory Design-Space Exploration,” arXiv preprint, 2026.
[arXiv:2608.23404v1](https://arxiv.org/abs/2608.23404v1).

[8] H. Horne, E. Spencer, A. Henningfield and A. Bisharat, “How the Dirty Set
Moves: Characterizing Schedule Reuse in Incremental Sparse Matrix
Multiplication,” arXiv preprint, 2026.
[arXiv:2610.19489v1](https://arxiv.org/abs/2610.19489v1).

[9] B. Hyun, T. Kim, D. Lee and M. Rhu, “Pathfinding Future PIM Architectures
by Demystifying a Commercial PIM Technology,” *HPCA*, 2024.
[doi:10.1109/HPCA57654.2024.00029](https://doi.org/10.1109/HPCA57654.2024.00029).

[10] J. Leskovec, J. Kleinberg and C. Faloutsos, “Graph Evolution: Densification
and Shrinking Diameters,” *ACM Transactions on Knowledge Discovery from Data*,
vol. 1, no. 1, 2007. Dataset: [SNAP ca-GrQc](https://snap.stanford.edu/data/ca-GrQc.html).
