# How to check and reproduce the evidence

A result is supported here by a chain: identified data and source → fixed search
work and query split → checked address trace → completed simulator service → paired
comparison → generated table or figure. A stored percentage alone is not the
evidence. The repository retains the raw measurements and the scripts for every
stage of that chain.

## Three different checks

| Check | What it establishes | What it does not establish |
| --- | --- | --- |
| `python3 scripts/check_results.py` | Completeness of the named matrix, valid raw/sidecar accounting, source and input identities, query separation, phase membership and selection rules. | It does not rerun every simulation. |
| `python3 scripts/analyze.py` | Regenerates numerical summaries and figures from the checked raw records, with paired intervals and input provenance. | It does not create independent performance observations. |
| Fresh simulation followed by `compare_reproduction.py` | Tests whether the same trace/model gives the same cycles, diagnostics and every query/phase interval in another result tree. | It does not validate the simulator against physical PIM hardware. |

The recorded environment uses GCC 15.1, Python 3.13 and CMake 3.30, with
Python package versions in `requirements.txt`. Start with those versions for exact
graph and numerical reproduction; another toolchain must pass the same input and
output checks rather than assuming graph construction is bit-identical.

The measured simulator is deterministic. Query-split and graph variation supply
the uncertainty studied in the thesis; rerunning an identical trace checks
reproducibility, not a new independent sample. Shared-host preprocessing seconds
are wall-clock observations and are expected to vary on another machine.

## Record counts and frozen protocols

The current matrix contains **2,069 distinct replay records**:

| Campaign | Records | Role |
| --- | ---: | --- |
| Earlier validated checkpoint | 1,289 | 791 original records, 494 published-layout/expansion comparisons and four command diagnostics |
| Scheduling sensitivity | 360 | Six further conditions, two footprints, three orders and ten splits |
| Training calibration | 420 | Seven conditions, two footprints, three orders and ten training splits |
| **Current total** | **2,069** | Retained replay records, not independent statistical experiments |

The three separately retained fresh reproduction checks are outside this count.
Frozen designs describe the campaigns as planned at their checkpoints:
[FOLLOWUP_DESIGN.md](FOLLOWUP_DESIGN.md) ends at 1,289 records, and
[SCHEDULING_DESIGN.md](SCHEDULING_DESIGN.md) starts from that checkpoint.
Their recorded text and hashes remain unchanged. Use this inventory and
[VALIDATION.md](VALIDATION.md) for the current totals.

## Full reproduction from a fresh checkout

Keep the reference checkout unchanged and use a second clone for the new run.
Choose the exact reviewed commit, not a moving branch, for both copies. The Git
history and validated-document archives identify earlier checkpoints separately.
The [commit identity correction](HISTORY_REWRITE.md) maps three original
checkpoint IDs to their current IDs; each corrected checkpoint has an identical
file tree. Use the corrected ID when following an older provenance reference.

```bash
git clone https://github.com/senqx/Thesis-PIM-ANN.git Thesis-PIM-ANN-reproduced
cd Thesis-PIM-ANN-reproduced
git checkout <reviewed-commit>
```

Requirements: Linux, a C++20 compiler, Make, CMake 3.15+, Python 3.12+ with
development headers, and curl. The recorded compiler/Python versions above are
the starting point for exact graph reproduction. Install the Python dependencies:

```bash
python3 -m venv .venv
. .venv/bin/activate
python3 -m pip install -r requirements.txt
```

Download the approximately 500 MB ANN-Benchmarks SIFT file:

```bash
mkdir -p .downloads
curl -L --fail --retry 2 https://ann-benchmarks.com/sift-128-euclidean.hdf5 \
  -o .downloads/sift-128-euclidean.hdf5
```

Expected source SHA-256:
`dd6f0a6ed6b7ebb8934680f861a33ed01ff33991eaee4fd60914d854a0ca5984`.
Conversion uses the first 100,000 training vectors and all 10,000 test vectors.
It records source/output hashes in `data/manifest.json`; the committed identity is
[`results/sift/dataset.json`](../results/sift/dataset.json). Search evaluates exact
neighbours over the indexed subset, rather than using full-million-vector ground
truth. Short, corrupt and nonfinite inputs are rejected.

Then run the complete sequence. The final command requires the document tools
described under [building the PDFs](#building-the-pdfs).

```bash
python3 scripts/setup_published.py
make -j2 test
bash scripts/setup_ramulator.sh --jobs 2
python3 scripts/prepare_sift.py
make test-simulator
python3 scripts/experiments.py all --seeds 10 --jobs 2
python3 scripts/strengthen.py all --jobs 2
python3 scripts/followup.py --jobs 2
python3 scripts/scheduling.py --jobs 2
python3 scripts/profiled_fetch.py --jobs 2
python3 scripts/analyze.py
bash scripts/build_docs.sh
```

`analyze.py` runs the complete evidence checker before generating outputs.
Tectonic and its bundle are needed only for PDF compilation.
The simulator/source setup verifies pinned archives; SIFT conversion verifies
the source hash. The complete matrix is 2,069 replays, including 420 calibration
runs. It is a substantial CPU workload; use the documented worker count or adapt
it to available resources. Exact runtime depends on the host. Large traces live
in `work/` and may be regenerated after cleanup.

The simulator pin is `7bead6cb7c4b03e095c6d4769ae3181a8e0bf6da`
(Ramulator 2.1 implementation). Setup builds the verified source and dependencies,
installs `simulator/thesis_trace.cpp`, and writes `ramulator2/build-manifest.json`.
`--offline` reuses verified local archives. Each input line represents one native
32-byte transaction; incompatible geometry and unaligned addresses fail.
The default model has one channel, Open pages, readiness-first FRFCFS, 64
uncompleted reads, a 32-entry read buffer and one issue opportunity per cycle.
Query/phase boundaries drain outstanding reads while retaining row state.

For partial campaigns, `experiments.py` supports `micro`, `sift`, `sensitivity`
and `synthetic`; run `sift` before `sensitivity`. `strengthen.py` supports
`controllers`, `graphs` and `mechanism`. The designs are recorded in
[RESEARCH_CLOSURE.md](RESEARCH_CLOSURE.md),
[FOLLOWUP_DESIGN.md](FOLLOWUP_DESIGN.md),
[SCHEDULING_DESIGN.md](SCHEDULING_DESIGN.md) and
[PROFILED_FETCH_DESIGN.md](PROFILED_FETCH_DESIGN.md).

**A fresh clone has no replay cache stamps.** The `.cache.json` files are ignored
by Git. The first complete run therefore invokes the simulator even though the
clone contains the committed raw results. Later runs may reuse valid local
caches, which is useful for recovery but must not be described as fresh
simulation. Keep the separate reference copy when running the full pipeline,
because the reproduction copy writes its own raw records and host timings.

Compare fresh scientific outputs with the unchanged reference result tree:

```bash
python3 scripts/compare_reproduction.py \
  --reference /path/to/reference/Thesis-PIM-ANN/results \
  --candidate results \
  --report work/full-reproduction-comparison.json
```

The default comparison checks every expected replay path, all simulator statistics,
model configuration, trace hash, accounting, command counts where present and all
query/phase intervals. It also compares the dataset manifest, query IDs and recall,
graph/mapping hashes, phase maps, retained profiles and calibration choices. It exits unsuccessfully on missing, malformed or different
evidence and retains the complete comparison report. Filesystem paths and
rebuilt-library hashes are separated from scientific equality; they can differ
across build directories. Numerical differences are not silently accepted because
an average is close. Inspect and explain a difference before calling a run a
reproduction. This tool compares evidence; the caller must actually run the fresh
pipeline before using that label.

## Fresh, independent checks of the vector-fetch path

After building the tools/simulator and preparing SIFT, a smaller command can
reconstruct the graph, queries, recall, mappings and logical demands in a new
directory, regenerate a selected trace, and invoke the simulator directly:

```bash
python3 scripts/reproduce_replay.py \
  results/followup/reference/seed1/roundrobin/bfs_512.json
python3 scripts/reproduce_replay.py \
  results/scheduling/seed1/alternate_mapping/roundrobin_512.json
python3 scripts/reproduce_replay.py \
  results/calibration/seed1/default/roundrobin_512.json
```

These examples check a positive default result, a harmful mapping/schedule
combination, and training calibration. The tool supports every scheduling and
calibration record and all reference-graph BFS follow-up modes. It never calls
the replay cache. Each run retains a fresh trace, raw JSON, phase/query timings,
logs and `comparison.json` beneath `work/reproductions/`, or a new explicitly
named output directory. It verifies regenerated source inputs and the trace hash
before comparing the fresh simulator output. A mismatch is a failure, not a
replacement of the committed reference result. These spot checks do not replace
the full-matrix reproduction above. The three checks executed in this revision
retain fresh raw evidence and comparison reports under
[reproduction/](../reproduction/README.md), separately from the experiment matrix.

## From each claim to its measurements

| Claim or comparison | Raw evidence | Derived summary / generator |
| --- | --- | --- |
| Row locality and completed time can disagree | `results/micro/`, `results/mechanism/` | `scripts/analyze.py`, `scripts/analyze_strengthening.py` |
| Initial fixed-traversal placement effects | `results/sift/seed*/timing/`, split and recall CSVs | `results/paired_summary.csv` |
| Controller and construction sensitivity | `results/robustness/`, `results/sensitivity/`, `results/ablations/` | `scripts/analyze_strengthening.py` |
| Published placements and expansion-boundary schedules | `results/followup/` | `results/followup_measurements.csv`, `scripts/analyze_followup.py` |
| Scheduling sensitivity | `results/scheduling/`, plus reused default follow-up records | `results/scheduling_pairs.csv`, `results/scheduling_summary.csv` |
| Training-selected fetch | `results/calibration/seed*/selection.json` and all three calibration orders; matching held-out records above | `results/profiled_fetch_selections.csv`, `results/profiled_fetch_pairs.csv`, `results/profiled_fetch_summary.csv` |

The fixed designs specify the comparison matrix and selection rule before their
respective campaigns. The selection extension was inspired by previously
inspected results and is labelled exploratory. No selected test timing is used
to choose an order. All alternatives and regressions remain available.

`doc/generated/provenance.json` records the inputs behind the current figures;
`results/artifact_manifest.json` inventories maintained source hashes. The
[validation record](VALIDATION.md) states what was actually executed in this
revision, distinguishing retained earlier checks from fresh reproduction checks.
Published algorithm adapters also have pinned source and differential tests.

## Reading the timing files

In bounded/sorted/round-robin replays, the simulator's query marker denotes an
expansion phase. Raw JSON `mean_query_cycles` is therefore a phase mean in those
modes. For reconstructed original-query service, use
`followup_measurements.csv` and `scheduling_measurements.csv` with their
`mean_original_query_cycles` field. `profiled_fetch_selections.csv` provides the
selected path's equivalent accounting. These intervals include gaps between
phases; lossless `.queries.csv.gz` sidecars and phase maps retain the details.

Paired intervals use ten reference split effects and a Student 95% interval with
nine degrees of freedom. Additional graph constructions use three matching splits
each and descriptive ranges. Per-query checks are descriptive, and shared-host
preprocessing seconds are expected to vary. Replays and reused queries must not
be counted as independent statistical replications.

## Building the PDFs

Install Tectonic 0.15.0 (on `PATH`, or at `.toolchain/bin/tectonic`) and Poppler's
`pdftotext` and `pdfinfo`. Then run:

```bash
make docs
```

This validates evidence, regenerates tables/figures, compiles both PDFs and checks
unresolved references and horizontal overflow. The build pins the TeX bundle to
`https://data1b.fullyjustified.net/tlextras-2022.0r0.tar`; the first compilation
needs network access. Packages are cached under `.toolchain/cache`.
With a populated cache, use `TECTONIC_OFFLINE=1 make docs`. To compile only the
document sources against already generated figures, run `bash scripts/build_docs.sh`.

## Storage and cleanup

The tracked artifact is about 397 MiB. Most of it is losslessly compressed raw
timing evidence: per-query/phase intervals, profiles and mappings. Removing those
files would prevent the complete checks above. Current PDFs and validated
document snapshots together are small; earlier work is indexed under
[`archive/`](../archive/README.md).

`work/` contains regenerable traces, mappings, logs and rendered page previews.
Experiments may need several GB of scratch space. Set `PIMANN_WORK=/path/to/scratch`
to use another filesystem, consistently across dependent campaign stages.

```bash
make clean-work
```

This removes only repository-local `work/`, legacy generated `traces/` and the
Ruff cache. It preserves committed evidence, datasets, built tools, verified
download archives and PDF-build dependencies. External `PIMANN_WORK` directories
are left for their owner to manage. `make clean` separately removes compiled
project binaries. Reproduction tools regenerate missing intermediates as needed.

After canonical data conversion is verified, the downloaded SIFT HDF5 is a
redundant copy and may be removed; repeating conversion then requires downloading
it again. The approximately 55 MB canonical `data/` files remain sufficient for
search and replay. Installer archives may likewise be removed after installation;
retaining the small pinned simulator/source archives supports offline rebuilding.

The reproducible claim is about this defined DRAM-service model. Reproducibility
does not remove its limits: fixed float32 traversal, hypothetical smaller
footprint, one corpus prefix, sequential queries and omitted execution costs.
