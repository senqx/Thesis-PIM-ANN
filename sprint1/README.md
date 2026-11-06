# Sprint 1 - Real-HNSW Graph-Aware Layout Pipeline

Replaces the earlier synthetic random-permutation trace with memory traces from
**real HNSW searches**, and compares physical data layouts on those traces -
including the proposed **query-aware** layout - at no cost to Recall@k.

Builds with just a C++20 compiler; hnswlib is vendored under `third_party/`.

## Build

```bash
make all            # builds run_bench (synthetic) and run_sift (real data)
```

## Synthetic benchmark (no dataset needed)

```bash
make bench          # 4 layouts x efSearch sweep -> bench_human.txt
make figures        # plots fig_bench_efsweep + fig_bench_metric from bench.csv
make synth          # emits test_{random,bfs,community,query_aware}.ldst for Ramulator
```

`make synth` builds a clustered corpus, runs real HNSW, and writes the four
held-out layout traces - so you can get cycle-accurate numbers (next section)
with no dataset download.

Layouts compared: `random` (baseline) < `community` (label-propagation
partitioning) < `bfs` (traversal order) < `query_aware` (proposed; learns
co-visitation from a TRAIN split, scored on a held-out TEST split).

## Real SIFT1M

Download SIFT1M (`sift_base.fvecs`, `sift_query.fvecs`) into `data/`, then:

```bash
make sift MAXBASE=100000     # quick first pass on 100k vectors
# or directly:
./run_sift data/sift_base.fvecs data/sift_query.fvecs 100000 500 200 64
```

This emits `sift_test_{random,bfs,community,query_aware}.ldst` - the held-out
test trace under each layout, in Ramulator LoadStoreTrace format.

## Cycle-accurate locality (real Ramulator)

With the main thesis repo's `ramulator2/` already built:

```bash
# synthetic traces (from `make synth`): prefix "test"
RAM=/path/to/Thesis-PIM-ANN/ramulator2 ./scripts/replay_ramulator.sh test

# real SIFT traces (from `make sift`): prefix "sift_test"
RAM=/path/to/Thesis-PIM-ANN/ramulator2 ./scripts/replay_ramulator.sh sift_test
```

Same HBM2 config as the main thesis (HBM2_8Gb @ 2000Mbps, FR-FCFS, Open row
policy, RoBaRaCoCh). Prints cycles / row-hit% / latency per layout, so the four
layouts are compared on identical cycle-accurate ground.

## Metrics note (important)

Report **inter-vector row-hit**, not the aggregate burst proxy. Each vector is
several 64B bursts; the intra-vector bursts are always row hits regardless of
layout and swamp the inter-vector transitions a layout actually controls. The
`allBurst%` column is shown only to demonstrate that distortion.

## Layout

```
src/ann/        hnsw_adapter (instrumented base-layer search), trace_collector,
                fvecs_loader, graph_view
src/layout/     memory_layout (interface), random/bfs/community/query_aware,
                covisitation_model
src/memory/     access_record (the layout-independent trace spine),
                address_emitter (-> Ramulator LD lines)
src/metrics/    recall_evaluator
src/layout_metrics.*   honest inter-vector row-hit + co-location
scripts/        replay_ramulator.sh
docs/           integration_plan.md
```
