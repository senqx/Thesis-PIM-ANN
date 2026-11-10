# DRAM locality in graph-based ANN

This repository contains Artashes Atanesyan's thesis and a reproducible experiment artifact.
It studies **DRAM stream service under explicit assumptions**, motivated by processing-in-memory.
It does not measure end-to-end PIM acceleration.

Start with [the thesis PDF](doc/pim_ann_thesis.pdf), [the short paper](doc/pim_ann_ieee.pdf),
or [the reading guide](doc/READING_GUIDE.md), which gives a path through the argument.
The [project overview](PROJECT_OVERVIEW.md) and [remediation record](doc/REVIEW_FIXES.md)
describe the project and link the review findings to repairs and validation.
For historical checkpoint references, the [commit identity correction](doc/HISTORY_REWRITE.md)
maps three original IDs to their current IDs without changing checkpoint contents.

The [research-position note](doc/RESEARCH_POSITION.md) explains the current RQs,
what related papers already established, and the claims supported at Master's
scope. Query-guided placement is prior art: the published NeurIPS 2022 paper by
Coleman et al. includes Porder. The thesis evaluates supplied RCM/Gorder/Porder
routines alongside its initial baselines.

The experiment uses stock float32 HNSW, all graph levels, non-overlapping
adjacency allocations, checked vector permutations, exact subset recall, and
native 32-byte HBM2 requests that all complete before replay terminates.
The hypothetical 128-byte footprint retains float32 search and is not an int8/PQ index.

Under the original flat replay, on ten paired SIFT100k splits, the query-aware heuristic uses **0.31% fewer cycles
than BFS at 512 bytes** (95% interval: 0.26–0.37% fewer), and **0.17% more at
128 bytes** (0.11–0.24% more). These intervals vary query splits and random/community
layout seeds on a fixed index and corpus. See [the generated paired results](results/paired_summary.csv)
for full precision and all baselines. Additional graph constructions reverse the
128-byte ranking, while the 512-byte query-aware advantage persists in the tested
flat-replay cases. The result therefore depends on graph construction as well as the memory
configuration. These small conditional differences establish neither optimality
of BFS nor application speedup. The earlier validated work remains in place. [The preservation guide](doc/RESULTS_PRESERVATION.md)
links its 44-page thesis, 5-page companion and supporting documents at commit
`71ce10b`. The separate [pre-review archive](archive/pre-review/README.md) contains
older material superseded by correctness repairs.

The expansion-bounded follow-up tests ordering only candidate reads available
inside a graph expansion. On the ten reference splits, round-robin on BFS uses
**14.58% fewer service cycles at 512 bytes** (95% interval: 14.51–14.64% fewer),
but **3.43% more at 128 bytes** (3.31–3.55% more). Address sorting is slower on
average at both widths under these default settings. Porder's bounded 512-byte advantage over BFS is smaller,
about **0.38%**. These are simulated service effects before scheduling, mapping,
computation and communication costs. The full thesis reports every selected graph
construction separately and does not add separately measured layout and
scheduling gains to predict an untested combination.

The scheduling sensitivity shows why footprint alone is insufficient. With 16
outstanding transactions, round-robin saves **33.08% at 512 bytes** and **10.61%
at 128 bytes** relative to matching original order. Under the alternative mapper,
it instead adds **112.71%** and **42.59%**. Candidate batches produce further
conditional outcomes; the [complete paired table](results/scheduling_summary.csv)
retains every setting and both fixed schedules.

The proposed PIM-oriented execution path profiles original, sorted and round-robin
fetch on **50 training queries per configuration**, then freezes the choice for
200 held-out queries. It matches the best fixed held-out order in all **140 tested
configuration/split cases**, selecting original/sorted/round-robin 40/10/90 times.
This is an exploratory engineering result using established schedules, not a new
HNSW algorithm or a guarantee for future workloads. At default 512 bytes, the
selected BFS path also uses **14.25% fewer cycles than Porder with original order**.
At default 128 bytes it selects original order and remains **1.35% slower than
Gorder**. The [full comparisons](results/profiled_fetch_summary.csv) and thesis
report fixed baselines, selection counts, query effects and calibration costs.
The proposed near-memory gather operation still needs an implementation that
charges computation, buffering, dispatch and communication before any application
speedup can be claimed.

## Verify and reproduce the claims

The [reproducibility guide](doc/REPRODUCIBILITY.md) explains three distinct tasks:
checking committed evidence, regenerating the analysis, and running fresh
simulations in a separate checkout. It maps each claim to raw files and gives a
full reproduction comparison command. A fresh clone has no replay-cache stamps.

For a smaller independent check, `scripts/reproduce_replay.py` rebuilds the HNSW
inputs, regenerates a chosen vector-fetch trace, bypasses the replay cache and
compares fresh cycles, diagnostics and every service interval with the retained
record. It preserves both outputs and reports mismatches as failures. The guide
includes positive, negative and calibration examples.

## Build and correctness checks

Requirements: Linux, a C++20 compiler, Make, CMake 3.15+, Python 3.12+ with development
headers, and curl. The recorded environment used GCC 15.1, Python 3.13, and CMake 3.30.
The analysis/data packages are pinned in `requirements.txt`.

```bash
python3 -m venv .venv
. .venv/bin/activate
python3 -m pip install -r requirements.txt
python3 scripts/setup_published.py
make -j2 test
```

The tests cover stock-search agreement (including ties and `ef < k`), address spans,
partial transactions, query boundaries, layout bijections, malformed input and valid
placement-quality permutations. A small synthetic run needs no dataset or simulator:

```bash
sprint1/run_study --max-base 8000 --train 300 --test 150 --output work/synthetic
```

The old separate `run_sift`, `run_dtype`, and multi-seed drivers have been replaced
by `run_study`; their historical sources are in the archive.

## Build the pinned simulator

```bash
bash scripts/setup_ramulator.sh --jobs 4
make test-simulator
make demo-ramulator
```

Setup downloads hash-verified Ramulator/dependency archives, builds them, applies
`simulator/thesis_trace.cpp`, and records `ramulator2/build-manifest.json`. The pin is
`7bead6cb7c4b03e095c6d4769ae3181a8e0bf6da` (Ramulator 2.1 implementation). This is the **corrected baseline**;
the simulator version behind the old archived results could not be recovered.
`--offline` uses already downloaded, verified archives. Re-running setup reapplies
the pin rather than silently keeping an arbitrary existing checkout.

The runner handles the in-tree Python/library paths. One input line denotes one
native **32-byte transaction**; use `--burst 32` with the root generators. The
frontend rejects incompatible simulator geometry and unaligned addresses.
Default settings: one channel, GenericDDR (at most one selected command per cycle),
Open policy, readiness-first FRFCFS, 64 uncompleted
reads, 32-entry read buffer, one issue opportunity per controller cycle. Query
boundaries drain outstanding reads while retaining row state. The follow-up also
drains between adjacency and candidate-vector phases. CPU/PIM computation and
transfer costs remain outside the model.

## Prepare SIFT100k

The public ANN-Benchmarks mirror is approximately 500 MB. The canonical conversion
uses the first 100,000 `train` records and all 10,000 `test` records.

```bash
mkdir -p .downloads
curl -L --fail --retry 2 https://ann-benchmarks.com/sift-128-euclidean.hdf5 \
  -o .downloads/sift-128-euclidean.hdf5
python3 scripts/prepare_sift.py
```

Expected source SHA-256:
`dd6f0a6ed6b7ebb8934680f861a33ed01ff33991eaee4fd60914d854a0ca5984`.
The conversion records source and output hashes in `data/manifest.json`.
[The committed dataset manifest](results/sift/dataset.json) identifies the evaluated files.
The driver computes exact neighbours over the indexed subset, rather than reusing
full-million-vector ground truth. It rejects short, corrupt and nonfinite data.

## Reproduce the evidence

```bash
python3 scripts/experiments.py all --seeds 10 --jobs 2
python3 scripts/strengthen.py all --jobs 2
python3 scripts/followup.py --jobs 2
python3 scripts/scheduling.py --jobs 2
python3 scripts/profiled_fetch.py --jobs 2
python3 scripts/check_results.py
python3 scripts/analyze.py
```

Baseline stages can also run separately: `micro`, `sift`, `sensitivity`, `synthetic`.
The additional campaign provides `controllers`, `graphs`, and `mechanism` stages.
Its fixed design is documented in [research closure](doc/RESEARCH_CLOSURE.md).
The [follow-up design](doc/FOLLOWUP_DESIGN.md) adds published RCM/Gorder/Porder
placements and expansion-bounded request schedules. The separate
[scheduling design](doc/SCHEDULING_DESIGN.md) tests outstanding limits, candidate
batches and address mapping. The [profiled-fetch design](doc/PROFILED_FETCH_DESIGN.md)
fixes a 50-training-query rule for choosing among three request schedules. `--pilot --jobs 1` runs its
first graph/split case; the full command includes that case and reuses valid replay
caches. `setup_published.py` verifies the NeurIPS supplementary archive and builds
both the adapter and an untouched reference for differential tests.
Run `sift` before `sensitivity`, which uses its first split. The full suite runs
hundreds of simulator conditions; allow several GB of working space. Set
`PIMANN_WORK=/path/to/scratch` to place large intermediates on another filesystem,
and use the same setting for the `sift` and `sensitivity` stages. Large
transaction traces from later splits and completed ablations are discarded after
replay; mapping files, logical traces, trace hashes, query timings and raw statistics
remain. Missing transaction traces are regenerated when needed.

* `results/`: committed raw JSON statistics, per-query timings, splits, accuracy,
  metadata and derived CSV summaries. Each timing JSON includes the full config,
  trace/library/frontend hashes and matching submitted/completed/classified counts.
* `work/`: regenerable logs, logical traces, mappings and selected transaction traces.
* `doc/generated/`: tables/plots generated from current results, with input hashes.
* `archive/2026-11-09-validated/`: previous validated documents and generated visuals,
  retained separately from the current narrative.
* `archive/2026-11-10-validated/`: all 57 documents from `94d3f1d`, preserving the
  previous 51-page thesis and seven-page paper. All 1,289 prior replays stay in place.
* `archive/pre-review/`: invalidated old evidence and obsolete drivers, excluded
  from the maintained build and current documents.

For follow-up bounded/sorted/round-robin runs, the simulator's query marker denotes
an **expansion phase**. Consequently, the raw JSON `mean_query_cycles` is a phase
mean in those modes. Use `results/followup_measurements.csv` and its
`mean_original_query_cycles` field for reconstructed original-query service; it
includes the gaps between phases. New `scheduling_measurements.csv` and
`profiled_fetch_selections.csv` provide equivalent original-query accounting for
the sensitivity and selected path. The lossless `.queries.csv.gz` files and
`phases.csv.gz` retain the accounting needed to check that reconstruction.

The analysis uses paired relative cycle differences per split and a Student 95%
interval with nine degrees of freedom. Three controller settings are repeated
across all ten splits. The other controller
settings and heuristic ablations use one fixed split. Three additional graph
constructions use three matching query splits each, with descriptive ranges
reported separately from the primary confidence intervals. Construction times are
shared-host wall-clock observations. The **2,069 retained replays** comprise the
previous 791, 494 follow-up comparisons, four scheduling diagnostics, 360 scheduling
sensitivity replays and 420 calibration replays. Calibration is training evidence,
not extra independent held-out replication. The new matrices use all ten reference
splits and two footprints, changing one memory/batch setting at a time.
The checker enumerates every expected result by name and verifies associated query
files, graph identities, recall and preserved primary trace hashes. Cache reuse
requires valid complete contents and matching hashes of outputs and sidecar files.
Missing prerequisite traces fail before controller sensitivity work starts.
A run fails on a command error or incomplete read accounting;
it does not append an apparently valid row after a failed simulation.

## Build the documents

Install Tectonic 0.15.0 (or put its binary at `.toolchain/bin/tectonic`) and Poppler's
`pdftotext`/`pdfinfo`. The build script pins the Tectonic bundle to
`https://data1b.fullyjustified.net/tlextras-2022.0r0.tar` and packages are cached under
`.toolchain/cache`. First compilation needs network access for TeX packages. Subsequent builds can
use `TECTONIC_OFFLINE=1 make docs` with the populated cache.

```bash
make docs
```

This regenerates tables/figures, compiles both PDFs, and checks unresolved references
and horizontal overflow. The long thesis is authoritative; the paper shares its
result tables, values and bibliography. Both follow the argument from search and
DRAM fundamentals through controlled results, robustness checks and practical
interpretation. Vector graphics illustrate the experiment pipeline, placement,
actual command issues and uncertainty in the measured differences. No old hard-coded figure is used.

The GitHub Actions workflow builds the pipeline, checks the pinned simulator,
validates committed results and regenerates numeric tables. The full SIFT campaign
is retained as research evidence rather than rerun on every push.
