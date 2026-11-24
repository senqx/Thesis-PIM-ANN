# When local reuse is worth its cost: standard sparse operations

This study extends the aggregation pilot with complete public sparse structures,
stronger baselines, native preparation, and a selector frozen before held-out
DPU timings. The [protocol](PROTOCOL.md) specifies the hypothesis, split, byte
budgets and failure criterion. It tests one simulated UPMEM DPU; it does not
measure hardware, energy, multi-DPU execution or a complete ML application.

**[Read the paired results and figures](results.md).** The tested linear selector
fails its declared practical-success criterion. Static retention still has useful
regimes; the results distinguish those two findings.

## Evidence inventory

The [manifest](manifest.json) identifies **485 distinct simulation records and
511 kernel invocations**. Thirteen records contain three invocations each.

| Role | Distinct records |
| --- | ---: |
| Calibration | 121 |
| Held-out primary comparison | 155 |
| Five-size capacity controls | 66 |
| Four/twelve-tasklet robustness | 50 |
| Boundary and changed-structure correctness | 28 |
| Three-invocation feature updates | 13 |
| Additional DRAM timing settings | 52 |

The [robustness report](robustness.md) includes repeated execution, structural
updates, feasible concurrency, five DRAM settings and host timing variation.
Its DRAM table has 65 rows because it reuses 13 primary records; those are not
additional runs. The 23,040 transfer/launch/lifetime combinations are analytical
scenarios, not simulation records or independent statistical experiments.

## Inputs and arithmetic

The public sources are from the [NIST Matrix Market](https://math.nist.gov/MatrixMarket/).
Exact URLs, compressed-source hashes, symmetry declarations and coordinate counts
are in [sources.json](sources.json); [sources.zip](sources.zip) preserves the public
files with their original headers and attribution. The matrices are contributed
Harwell–Boeing datasets, not newly created or owned by this project.

| Role | Matrices | Purpose |
| --- | --- | --- |
| Calibration | bcsstk01, bcsstk06, west0067 | Fit cycle models and select a fixed policy before held-out timings |
| Held-out evaluation | 494_bus, 1138_bus, can__144, can__256 | Test on power-network and Cannes families absent from calibration |
| Controlled | Uniform and clustered rows at five source-table sizes | Isolate configured-capacity effects with fixed rows and nonzero counts |
| Correctness | Empty rows/groups, trailing dimensions, scalar padding and changed values | Check the representation and repeated execution boundaries |

The seven public matrices have 48–1,138 original rows and 294–7,860 expanded
nonzero coordinates. We preserve their complete nonzero structures, expand
declared symmetry and assign positive integer weights `1 + (row + 3*column) % 3`.
**These are structural projections, not the original floating-point problems.**
Their operations are standard weighted SpMV (`y = A x`) and SpMM (`Y = A X`).
Columns and rows are padded to multiples of four with empty positions.

SpMV uses one int32 value in an aligned 8-byte record. SpMM uses 2, 4, 8, 16
and 32 values: five actual widths from 8 to 128 bytes. CPU references check all
weighted output values and prove that the tested sums fit int32. No neighbors
are sampled and no repeated contribution is silently removed. Each public input
is one matrix; its width variants are related experimental conditions.

## The compared implementations

| Policy | What it does | Costs included |
| --- | --- | --- |
| stream128 / stream512 | Read CSR entries in 128/512-byte chunks; fetch each source on demand | Row pointers, indices, weights, source reads and output writes |
| hot | Rank sources by frequency, reorder the source table and indices, retain a fitting prefix | Ranking, rewrite, feature permutation on refresh, preload, barrier and per-reference residency test |
| full | Load the complete source table when it fits the configured linked allocation | Preload and barrier on every invocation |
| batch | Prepare unique source IDs plus weights and ordered one-byte row/slot codes | Native construction, dictionary/header bytes, loading and interpretation; 512-byte private payload |
| bcsr2 / bcsr4 | Reuse source blocks across 2x2/4x4 sparse blocks | Native conversion, zero padding, block metadata, extra source reads and complete weighted arithmetic |

BCSR applies SparseP's established block-reuse principle; these kernels are not
a reproduction or performance comparison of the complete SparseP system. Hot
placement is conventional and follows DRIM-ANN's frequency-per-capacity precedent.
Nothing here claims invention of caching, sparse formats or cost-model selection.

The earlier [runtime-cache footprint screen](../access-plan/footprints.csv)
found its direct-mapped history cache 55–75% slower than its tuned streaming
comparators at 8, 64 and 256 bytes. That motivated keeping this study to the
listed strategies. It does not rule out all cache organizations on these matrices.

The primary configuration is eight tasklets, assigned groups of four rows.
All methods share a 65,536-byte WRAM ceiling. The upstream linker reserves
49,152 bytes for stacks regardless of active tasklets. Our conservative formula
reserves 8 KiB for shared residency at the smaller widths and 4 KiB at 128 bytes;
linked allocations are checked separately. This is a tested allocation policy,
not proof that no alternative arrangement could fit a larger table.

The primary comparison permits no extra installed matrix/plan bytes or local
read-plus-write bytes relative to CSR streaming on that same input and width.
Results outside this budget remain visible in unconstrained comparisons. Full
residency points are omitted where infeasible, not extrapolated. Non-residency
policies have five executed points in each capacity and SpMM-width sweep.

## What “total cost” means here

Native C++ preparation, inspection and feature refresh are timed separately,
with 31 samples after three warmups. Feature synthesis and filesystem output
are outside those timings; refresh copies or permutes an already available
source matrix. The same executable supplies the representations actually used
by the DPU. Raw samples and process peak RSS are preserved; process RSS includes
runtime/input/output storage and is not a precise allocator-level peak.
Native sample intervals exclude destruction of the timed representation.
Simple-rule dispatch is not separately timed. The remaining margin must cover
these costs together with any additional deployment overhead.

For a prepared structure used `K` times, the scenario adds native setup, metadata
installation and `K` times complete simulated kernel time, host feature refresh,
feature upload and output retrieval. The primary illustrative effective bandwidth
is 80 MB/s per DPU; sensitivity uses 20–320 MB/s and 0/10/100 microsecond launches.
There is no assumed overlap. Code is compiled and loaded before this cost interval;
SDK/program-loading cost, initial file parsing, multi-DPU partitioning and
application integration are outside it. An additional deployment cost can erase
the reported saving. These totals are **conditional models, not end-to-end times**.

Native candidate construction and structural inspection count even when the
selector rejects the candidate. The model assumes candidate plans are retained
in host memory until selection; this can require their combined metadata storage.
Artifact file I/O is not part of that deployment model. Candidate source copies
can be released after inspection and the selected source is refreshed per use.

Calibration is a one-time cost separate from deployed-rule totals. Its simulated
work, modelled serial cost and host fitting time are reported separately. The
fixed policy also depends on calibration; the capacity-first and reuse rules do
not. Recalibration after a hardware/compiler/configuration change is required
before treating the model as validated there.

## Reproduce and inspect

The study uses the [pinned platform](../../docs/PLATFORM.md). Auditing and frozen
replay require no new dataset download or compiler:

```sh
python3 scripts/decision_artifact.py verify
python3 scripts/decision_artifact.py replay
```

The archive preserves exact linked images, all input/output bytes, simulator
options and counters. Replay uses a fresh directory under `runs/decision-study/`.
Source rebuilds may produce different instruction images because the upstream
Go linker iterates maps in unspecified order; keep those results separate.
The [SDK runtime notices](../wram/THIRD_PARTY_NOTICES.txt) apply to linked images.

The default replay checks three records, including a three-invocation case.
To select any retained record, or replay the entire inventory, use a new path:

```sh
python3 scripts/decision_artifact.py replay --key 494_bus-w2-hot-t8-e0-dram0.5 --replay-directory runs/decision-check
python3 scripts/decision_artifact.py replay --all --replay-directory runs/decision-full-replay
```

Full replay can take hours; it reproduces every retained parameter setting and
compares every simulator counter. It needs no native preparation. To regenerate
the derived tables from retained native samples and simulator records, run
`python3 scripts/decision_report.py`. Plot generation uses the pinned
[document dependencies](../../thesis/requirements.txt). Do not rerun `evaluate`
just to rebuild a figure: it measures prediction overhead anew.

To rebuild source, first compile with the existing SDK container, using the
same unprivileged, network-disabled invocation documented for the other studies:

```sh
docker run --rm --network none --read-only --cap-drop ALL \
  --security-opt no-new-privileges --user "$(id -u):$(id -g)" \
  --tmpfs /tmp:rw,nosuid,nodev \
  --mount "type=bind,src=$PWD,dst=/work" \
  thesis-upmem-compiler:2023.1.0 python3 scripts/decision_study.py compile
python3 scripts/decision_study.py native --run-directory runs/decision-rebuild
python3 scripts/decision_study.py run --split smoke --run-directory runs/decision-rebuild
python3 scripts/decision_study.py run --split calibration --run-directory runs/decision-rebuild
python3 scripts/decision_study.py run --split heldout --run-directory runs/decision-rebuild
python3 scripts/decision_study.py run --split controlled --run-directory runs/decision-rebuild
```

These rebuild commands reuse the retained structural inputs; raw source files
are needed only to regenerate them. Existing retained phase tables are preserved;
new phase tables go into the selected run directory. Do not overwrite the frozen
model after inspecting evaluation timings. The source build uses DPU `-O2` and
native `-O3 -std=c++17`. Native timing varies with the host and its load.

The [novelty audit](../../docs/NOVELTY_AUDIT.md) distinguishes established mechanisms
from the empirical contribution. This study can establish a scoped decision or
failure case; it cannot establish universal priority or hardware validity.
