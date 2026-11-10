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

## Full reproduction from a fresh checkout

Keep the reference checkout unchanged and use a second clone for the new run.
Choose the exact reviewed commit, not a moving branch, for both copies. The Git
history and validated-document archives identify earlier checkpoints separately.

```bash
git clone https://github.com/senqx/Thesis-PIM-ANN.git Thesis-PIM-ANN-reproduced
cd Thesis-PIM-ANN-reproduced
git checkout <reviewed-commit>
```

Follow the root README to install its pinned Python dependencies, build the C++
tools and verified simulator source, and download/convert the hash-identified SIFT
file. Then run the complete sequence:

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
The dataset must be downloaded to the README's documented location before
conversion. Tectonic and its bundle are needed only for PDF compilation.
The simulator/source setup verifies pinned archives; SIFT conversion verifies
the source hash. The complete matrix is 2,069 replays, including 420 calibration
runs. It is a substantial CPU workload; use the documented worker count or adapt
it to available resources. Exact runtime depends on the host. Large traces live
in `work/` and may be regenerated after cleanup.

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

The reproducible claim is about this defined DRAM-service model. Reproducibility
does not remove its limits: fixed float32 traversal, hypothetical smaller
footprint, one corpus prefix, sequential queries and omitted execution costs.
