# First Sprint — Architecture & hnswlib Integration Plan

Goal of the sprint: replace the synthetic random-permutation trace with memory
traces from **real HNSW searches**, and compare Random vs BFS physical layouts
on those real traces — without degrading Recall@k. This is the milestone that
turns the current proof-of-concept into a defensible result.

## The pipeline

```
          hnswlib index
                │  (instrumented search)
                ▼
        TraceCollector  ──►  AccessTrace          (logical: node ids, kinds)
                                   │
   GraphView ──► MemoryLayout ─────┤  slotOf(nodeId)
                                   ▼
                           AddressEmitter  ──►  Ramulator LD trace  (bytes)
                                   │
                                   ▼
                      Ramulator 2.1 (existing runner)  ──►  row-hit rate

   (parallel path)  ground truth + results ──► RecallEvaluator ──► Recall@k
```

The spine is **`AccessRecord`** (`memory/access_record.h`): a layout-independent
record of *what logical thing* was touched, in issue order. The search produces
it once; each layout re-prices it into addresses. This separation is what lets
us replay one real trace under Random, BFS, METIS, ... without re-running the
search, and guarantees every layout sees identical access *order* — only
*placement* changes.

## Why these boundaries

- **`GraphView`** decouples layout strategies from hnswlib. BFS (this sprint)
  and METIS/Louvain (later) only need topology + vector dimensions, never
  hnswlib internals.
- **`MemoryLayout`** is the thesis contribution surface. It maps a logical node
  to a physical *slot* (bijection). Everything else is machinery around it.
- **`AddressEmitter`** is deliberately separate from the layout: vectors,
  adjacency lists, and metadata live in distinct address regions, so a layout
  can co-locate vectors without disturbing the others. Later sprints can add an
  adjacency layout by giving the emitter a second mapping.
- Keeping **Vector vs Adjacency** reads as distinct `AccessKind`s is essential:
  they have different sizes and locality, and the roadmap's whole critique is
  that lumping them (as the synthetic model does) hides real behaviour.

## hnswlib instrumentation approach

hnswlib is header-only (`hnswlib/hnswlib.h`), vendored under
`third_party/hnswlib/`. We do **not** fork its algorithm. Two options for
capturing accesses, in preference order:

1. **Replay-from-visited (preferred, non-invasive).** Run the stock
   `searchKnn`, then reconstruct the access sequence from the same primitives
   the search used: for each expanded node, emit one `Vector` access (distance
   computation) and one `Adjacency` access (neighbour-list read). This keeps
   hnswlib pristine (just update the submodule to upgrade) at the cost of
   re-deriving order from the search's candidate expansion.

2. **Direct hook (fallback, if order fidelity needs it).** Add a single
   compile-time callback at the two sites in `searchBaseLayerST` where hnswlib
   (a) reads `data_level0_memory_` for a distance and (b) reads the neighbour
   list. One `#ifdef PIMANN_TRACE` guard, two call sites. Captures exact order
   but touches the vendored file.

Start with (1); escalate to (2) only if the base-layer access order proves hard
to reconstruct faithfully. Either way the collector records the *base layer*
(level 0) traffic, which dominates footprint and bandwidth.

## This sprint's scope (and what is deferred)

In: hnswlib adapter + GraphView, trace collector (vector/adjacency split),
Random + BFS layouts, Recall@10/100, address emitter, first Random-vs-BFS
locality report on SIFT1M base-layer traces.

Deferred: METIS/Louvain/query-aware layouts, GIST/DEEP datasets, DRAM
sensitivity sweep, construction-overhead study, full ablation. Those are later
roadmap phases and should not block the core validation.

## Open design questions to confirm before coding step 2

1. **Trace scope:** base layer only (recommended) vs all levels. Base layer is
   >90% of traffic and keeps the first result clean.
2. **dtype:** SIFT is uint8 natively but hnswlib's L2 space is float32. Use
   float32 end-to-end (dtypeBytes = 4) for a faithful hnswlib run, and note that
   the earlier synthetic study used int8. The byte-budget law still applies;
   only the constant changes.
3. **Instrumentation path:** confirm we start with the non-invasive
   replay-from-visited approach.
```
