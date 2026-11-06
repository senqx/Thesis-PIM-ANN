# Sprint 1 Findings: Does Graph-Aware Data Layout Help Real Graph-ANN on PIM?

## What I set out to test

My earlier results showed that, for graph-based ANN (HNSW), random memory
access destroys DRAM row-buffer locality, and that a *cluster-ordered data
layout* could in principle recover it. But that evidence came from a synthetic
random-access trace, not from a real index. The honest next question - and the
one my own thesis flags as a limitation - was whether a layout informed by the
real search behaviour of HNSW actually improves locality on real data, without
hurting search quality.

So I built a faithful pipeline: a real HNSW index (hnswlib), instrumented to
record the exact base-layer memory accesses of real queries, separating vector
reads from adjacency reads. I then compared four physical layouts by replaying
the resulting traces through the same cycle-accurate Ramulator HBM2 model used
in the rest of the thesis:

- **Random** - a locality-hostile control.
- **Community** - structural partitioning (label propagation), a dependency-free
  stand-in for METIS/Louvain.
- **BFS** - place nodes in breadth-first traversal order of the graph.
- **Query-aware (proposed)** - learn, from a *training* set of queries, which
  nodes are actually read together, and co-locate those; evaluate on a *disjoint
  held-out* query set so any gain reflects generalisation.

Crucially, layout never changes the search result, so **Recall@10 is identical
across all four layouts** - locality is bought at zero accuracy cost by
construction.

## What happened

### On synthetic clustered data, the proposed layout led

Using a synthetic corpus of Gaussian clusters (20k vectors, dim 128), the
query-aware layout gave the best inter-vector row-hit rate, and its advantage
grew with search effort (efSearch). On cycle-accurate HBM2 it also gave the
fewest cycles. This looked like a positive result.

### On real SIFT1M, the advantage disappeared

Repeating the experiment on 100,000 real SIFT1M base vectors (dim 128), through
the same cycle-accurate simulator, the picture reversed. Measured on the honest
inter-vector row-hit metric and on full Ramulator timing:

| Layout | Cycles | Row-hit % | Avg latency | Inter-vector row-hit % |
| :-- | --: | --: | --: | --: |
| Random | 2,482,246 | 86.28 | 75.10 | 0.004 |
| Community | 2,479,971 | 86.32 | 75.04 | 0.129 |
| Query-aware (proposed) | 2,479,476 | 86.66 | 74.98 | 1.005 |
| **BFS** | **2,471,117** | 86.61 | **74.79** | **1.365** |

**BFS is the best simple layout on real data** - fewest cycles, lowest latency,
and the highest inter-vector row-hit rate. The proposed query-aware layout does
not beat it; it only ties on aggregate row-hit (86.66 vs 86.61, within noise).
The entire spread across all four layouts is tiny: 0.45% in cycles, 0.38 points
in row-hit.

## Why the synthetic win did not transfer

This is the important part, and it is a genuine finding rather than a bug.

**On real HNSW, the graph already encodes the access pattern.** HNSW connects
each node to its nearest neighbours, and a query walks those edges. So the nodes
a query visits together are, by construction, graph neighbours. BFS ordering
co-locates graph neighbours - which means it is *already* co-locating the
co-visited nodes, for free, with no training and no query log. A learned
query-aware model has almost nothing extra to exploit, because adjacency is
already an excellent predictor of co-visitation.

On the synthetic data this was not true: the artificial Gaussian clusters I
imposed did not line up with the graph structure, so the query-aware model could
exploit a signal that BFS could not see. That gap is exactly what flattered the
proposed method - and it is exactly the kind of artefact my thesis warns about.

**Layout barely moves the needle at all on real SIFT.** Even BFS versus random is
under half a percent of cycles. This follows directly from my earlier byte-budget
result: at dim 128 in float32, a single 2 KB DRAM row holds only about four
vectors, so the co-location budget is tiny and intra-vector bursts dominate the
trace. There is simply little inter-vector locality available to recover.

## What this means for the thesis

The honest contribution of this sprint is **not** "query-aware layout beats
BFS." On real data that claim is false. The contributions are:

1. **A faithful, reproducible methodology** for studying real graph-ANN memory
   behaviour: instrumented HNSW tracing (vector vs adjacency), pluggable
   layouts, and cycle-accurate replay - with recall held fixed.
2. **A negative result with a mechanism:** learned query-aware placement does not
   outperform free traversal-order (BFS) placement on real HNSW, because graph
   adjacency already captures co-visitation. Simple BFS ordering is a strong,
   zero-cost baseline that is hard to beat.
3. **Confirmation that layout gains are marginal on real graph-ANN at float32
   dim-128**, consistent with the byte-budget law: large vectors leave little
   room per DRAM row for inter-vector locality to matter.

This also vindicates the methodology of the whole thesis. Three times now, a
convenient result from a simplified setting has been overturned by the real
cycle-accurate simulator: the teaching model mispredicted reordering; the
aggregate row-hit proxy hid the real signal; and now a synthetic corpus
flattered a layout that real data does not support. The consistent lesson -
*distrust the convenient result and verify on reality* - is the thing I am most
confident defending.

## Testing the one place the law says layout *should* help: int8

The result above is at dim 128 **float32**, where a 512-byte vector means only
about four fit in a 2 KB DRAM row - a tiny co-location budget. My own
byte-budget law predicts that if vectors were *smaller*, more would fit per row
and layout should matter *more*. Product Quantization and int8 storage do
exactly that: a 128-byte int8 vector lets ~16 fit per row. So this is not a
parameter I tuned to rescue the method - it is the single place the theory says
layout has the most to work with. If the learned layout were ever going to win,
here is where.

I re-ran all four layouts on real SIFT1M at both encodings (same honest
inter-vector row-hit metric):

| Layout | float32 (4 vec/row) | int8 (16 vec/row) |
| :-- | --: | --: |
| Random | 0.004 | 0.020 |
| Community | 0.129 | 0.609 |
| Query-aware (proposed) | 1.005 | 1.151 |
| **BFS** | **1.365** | **2.103** |

Two things happen, and both are informative.

**The byte-budget law holds on real data.** Every layout improves with the
larger int8 budget - confirming, on real graph traces, the same mechanism the
main thesis found synthetically: more co-visited data per row means more
recoverable locality.

**But the bigger budget does not rescue the proposed method - it widens BFS's
lead.** BFS is best at *both* encodings, and its margin over query-aware
*grows*: BFS beats query-aware by 0.36 points at float32 and by 0.95 points at
int8. BFS soaks up almost all of the extra budget (1.37 -> 2.10) while
query-aware barely moves (1.01 -> 1.15). The reason is the same as before: on a
real graph the neighbours you traverse already *are* the co-visited nodes, so
giving BFS more room per row simply lets it co-locate more of them for free. The
learned model has nothing extra to capture.

This settles the central question. We have now tested the proposed layout on
real data at the encoding where it had the best chance, and it still does not
beat the simplest baseline. The negative result is robust across vector
encoding, not an artefact of one setting. (See `results_dtype_real.csv` and
`fig_dtype_byte_budget.png`.)

## Remaining open question (not a rescue attempt)

One genuinely *different* question is still open, and I frame it as
characterisation, not as a way to make query-aware win:

- **Full-scale and other datasets.** 1M vectors and higher-dimensional sets
  (GIST, dim 960) would test whether the marginal-gain finding and BFS's
  strength hold across scale and dimension. The expectation, given everything
  above, is that simple traversal-order placement remains the baseline to beat.
