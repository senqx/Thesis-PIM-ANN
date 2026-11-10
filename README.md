# DRAM locality in graph-based ANN

[![Artifact checks](https://github.com/senqx/Thesis-PIM-ANN/actions/workflows/ci.yml/badge.svg)](https://github.com/senqx/Thesis-PIM-ANN/actions/workflows/ci.yml)

**When a graph search needs the same data, can changing its placement and request
order make memory finish sooner?**

This repository contains Artashes Atanesyan's Master's thesis and its reproducible
experiment artifact. It studies HNSW approximate nearest-neighbour search on
SIFT100k using a pinned HBM2 DRAM simulator, motivated by processing-in-memory (PIM).
The measurements describe **simulated memory service**; application and PIM
speedup require a complete implementation with computation and communication costs.

```mermaid
flowchart LR
    A[HNSW search] --> B[Fixed logical reads]
    B --> C[Placement and request order]
    C --> D[HBM2 simulation]
    D --> E[Paired service comparisons]
```

## Start here

**Current evidence: 2,069 replay records** = the previous validated checkpoint
of **1,289**, plus **360 scheduling sensitivity** and **420 training calibration**
runs. These are retained records, not 2,069 independent statistical experiments.
The PDFs below and their [validation record](doc/VALIDATION.md#current-document-set)
belong to the same Git revision; the record gives their page counts and SHA-256 hashes.
Page counts include all PDF pages, including the title page and front matter.

| Purpose | Document |
| --- | --- |
| Read the argument | [IEEE companion, 8 pages](doc/pim_ann_ieee.pdf) |
| Study the methods and results | [Full thesis, 68 pages](doc/pim_ann_thesis.pdf) |
| Follow the ideas without ANN/DRAM specialisation | [Reading guide](doc/READING_GUIDE.md) |
| Understand the research questions and prior work | [Research position](doc/RESEARCH_POSITION.md) |
| Check or reproduce a claim | [Reproducibility guide](doc/REPRODUCIBILITY.md) |
| See which checks were performed | [Validation record](doc/VALIDATION.md) |
| Prepare the defence | [Presentation, 14 slides](doc/pim_ann_defence.pdf) and [speaking guide](doc/READING_GUIDE.md#defence-presentation) |

All current results use the corrected, pinned **Ramulator 2.1 implementation**
(`7bead6cb7c4b…`) with native **32-byte transactions**. The 1,289-record checkpoint
uses that same baseline and remains part of the current evidence. Only the
[pre-review material](archive/pre-review/README.md) was superseded by correctness
repairs; it is excluded from current comparisons. See the
[baseline history](doc/REPRODUCIBILITY.md#corrected-baseline-and-historical-evidence)
before reproducing an older result. This README is the maintained project overview.

## What the study shows

Row reuse and bank parallelism can favour different layouts or request orders.
The main HNSW comparisons cover **512-byte float32 vectors** and a **hypothetical
128-byte footprint**. Both use the same recorded float32 search; the smaller
footprint is not an implemented quantised index.

For example, round-robin vector fetching versus original-order BFS gives:

| Memory configuration | 512 bytes | 128 bytes |
| --- | ---: | ---: |
| Default, 64 outstanding reads | −14.58% | +3.43% |
| 16 outstanding reads | −33.08% | −10.61% |
| Alternative address mapping | +112.71% | +42.59% |

Values are mean paired changes in completed service cycles over ten query splits;
negative means fewer cycles. [Full results and 95% intervals](results/scheduling_summary.csv)
include all seven configurations, sorting and both footprints.

A small training profile chooses among original, sorted and round-robin fetch
orders, then freezes the choice for held-out queries. It matches the best fixed
held-out order among those three in all 140 cases: seven settings × two footprints
× ten splits on one workload. This is an exploratory matrix result, not a general
success probability. Individual-query regressions remain, and the selected path does not
beat every published placement. The thesis compares it with RCM, Gorder and
Porder and reports profiling costs and model limitations.

For PIM, the thesis develops a concrete [host/near-memory execution sketch](doc/READING_GUIDE.md#the-final-step-choose-the-execution-order-from-training):
host control supplies discovered candidates, and a proposed engine gathers resident
vectors and returns distances. The scheduling evidence guides that interface;
the engine and its communication costs still need implementation and measurement.

## Quick start

Use Linux with a C++20 compiler, Make, Python 3.12+ and curl. From the repository
root, install the pinned Python packages and run the code checks:

```bash
python3 -m venv .venv
. .venv/bin/activate
python3 -m pip install -r requirements.txt
python3 scripts/setup_published.py
make -j2 test
```

These tests need no SIFT download or simulator. For a small synthetic HNSW run:

```bash
sprint1/run_study --max-base 8000 --train 300 --test 150 --output work/synthetic
```

The [reproducibility guide](doc/REPRODUCIBILITY.md) contains the complete simulator
setup, dataset download, experiment commands, fresh-result comparison and PDF
build instructions. It distinguishes validating stored records from rerunning
simulations. The SIFT download path is `.downloads/sift-128-euclidean.hdf5`.
GitHub Actions builds and tests the tools, validates the retained
matrix and checks numerical table regeneration.

## Repository layout

| Path | Contents |
| --- | --- |
| [`doc/`](doc/) | Thesis and paper sources/PDFs, reader guides, protocols and generated figures |
| [`sprint1/`](sprint1/) | HNSW tracing, vector placement and search correctness tests |
| [`src/`](src/), [`simulator/`](simulator/) | Controlled trace tools and the simulator frontend |
| [`scripts/`](scripts/), [`tests/`](tests/) | Setup, experiments, analysis, reproduction and checks |
| [`results/`](results/) | Raw evidence and derived summaries for 2,069 replay records |
| [`reproduction/`](reproduction/) | Three separately retained uncached reproduction checks |
| [`archive/`](archive/) | Earlier validated documents, superseded material and review history |

The tracked artifact is about **397 MiB**, mostly losslessly compressed timing
records needed to check individual queries and phases.
[The campaign inventory](doc/REPRODUCIBILITY.md#record-counts-and-frozen-protocols)
explains the counts retained in historical protocols.
Large local intermediates go in ignored `work/`; `make clean-work` removes those
files without removing committed results, datasets, tools or document archives.
See [storage and cleanup](doc/REPRODUCIBILITY.md#storage-and-cleanup) for details.

## License

The project is [MIT licensed](LICENCE). Third-party code and data retain their
respective notices; see [HNSW provenance](sprint1/third_party/README.md) and the
pinned source setup in the reproduction guide.
