# Previous study: concise record

**Historical evidence only.** The complete artifact is preserved at commit
[`fcab5d2be844dd1097f7f0ae13bbe500a12f8caf`](https://github.com/senqx/Thesis-PIM-ANN/tree/fcab5d2be844dd1097f7f0ae13bbe500a12f8caf),
tag `archive/dram-service-2026-11-13`.

The study replayed fixed HNSW searches on SIFT100k using a pinned Ramulator 2.1
HBM2 configuration with 32-byte transactions. HNSW used M=16,
efConstruction=200, efSearch=64 and k=10. The main comparisons used ten paired
query splits. The artifact retained **2,069 replay records**, not 2,069
independent experiments.

Results below are changes in **simulated completed DRAM-service cycles**;
negative means fewer cycles. The 512-byte footprint represents float32 vectors.
The hypothetical 128-byte footprint reuses the same float32 traversal; it is
not a tested quantized search.

| Comparison | 512 bytes | 128 bytes |
| --- | ---: | ---: |
| Query-aware placement vs BFS placement, default flat replay | −0.31% | +0.17% |
| Round-robin vs original order on BFS, default expansion-bounded replay | −14.58% | +3.43% |
| Same scheduling comparison with alternative address mapping | +112.71% | +42.59% |

The first 512-byte comparison saved 97.3 cycles/query; the second saved
5,802.4. More row hits did not reliably mean shorter service. Availability,
parallelism, footprint and mapping could change or reverse the recommendation.

A training-based selector matched the best tested fixed schedule in 140/140
held-out cases. It selected the same order within each configuration, added no
benefit over its correctly chosen fixed winner, and was exploratory because
the design followed inspection of test outcomes.

**Limits:** these are memory-service findings. Distance computation, CPU/DPU
execution, host communication, implementation overhead, application latency
and energy were not measured. Ramulator is a DRAM timing simulator, not
inherently a processing-using-memory execution platform. The findings remain
useful, but do not validate the new adaptive-prefetching hypothesis.

Recover the full study in a separate directory:

```sh
git fetch origin tag archive/dram-service-2026-11-13
git worktree add --detach ../Thesis-DRAM-archive archive/dram-service-2026-11-13
```

Read its `doc/REPRODUCIBILITY.md` and `doc/VALIDATION.md` for methods and
qualification of the results. Downloaded dependencies and regenerable caches
were removed locally; their archived setup instructions remain in Git.
