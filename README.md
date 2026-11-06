<div align="center">

# Thesis‑PIM‑ANN

### Memory‑Locality Limits of Graph‑Based Approximate Nearest Neighbour Search on Processing‑in‑Memory

*A small, fully reproducible research artifact — builds with just a C++ compiler, scales up to the real Ramulator cycle‑accurate DRAM simulator.*

![C++20](https://img.shields.io/badge/C%2B%2B-20-00599C?logo=cplusplus&logoColor=white)
![Build](https://img.shields.io/badge/build-make-427819)
![Simulator](https://img.shields.io/badge/validated%20on-Ramulator%202.1%20(HBM2)-1F6F8B)
![License](https://img.shields.io/badge/license-MIT-lightgrey)

</div>

---

> 🧭 **New here?** Read **[`PROJECT_OVERVIEW.md`](PROJECT_OVERVIEW.md)** first — a
> plain‑language tour of the whole project (no background needed): what we did,
> the questions we asked, what worked, and what honestly did **not**.

> 📁 **This repo has two layers — read both before judging the claims.**
> **(1) Root (`src/`, `doc/`)** — the core study: a *controlled microbenchmark* that
> isolates access‑pattern effects on DRAM locality, using SIFT‑dimensioned
> **synthetic** traces, validated cycle‑accurately on Ramulator HBM2.
> **(2) [`sprint1/`](sprint1/)** — the follow‑up that closes the realism gap:
> a **real HNSW index** (hnswlib) over the **real SIFT1M** dataset, with
> graph‑aware layouts, recall held fixed, replayed through the same simulator.
> The root establishes the *mechanism*; sprint1 tests whether it survives on real
> graph‑ANN. **Its headline is an honest negative result** (a learned layout does
> not beat simple BFS on real data) — see [`sprint1/docs/findings.md`](sprint1/docs/findings.md).

---

## 📌 The one‑sentence idea

> **Approximate Nearest Neighbour (ANN) search is memory‑bound, so it is a natural Processing‑in‑Memory (PIM) target — but *how* it reads memory decides whether PIM helps.**
> *Cluster‑based* ANN (IVF/PQ) reads memory **sequentially** and loves PIM. *Graph‑based* ANN (HNSW) reads it **randomly**, destroying DRAM row‑buffer locality — which is exactly why graph‑ANN‑on‑PIM is an open problem.

This repo **measures that gap** on a real cycle‑accurate simulator, shows that software **reordering does *not* fix it** (the memory controller already reorders), and that **data layout fixes it completely** — co‑locating just ~16 vectors per cluster recovers full sequential‑scan locality.

---

## 🎯 Headline results

The **DRAM‑locality numbers below are measured on real HBM2 timing (Ramulator 2.1)** — row‑hit rate, cycles, and latency. They are the load‑bearing evidence of this project.

| Access pattern | DRAM row‑hit rate | Cycles (Ramulator HBM2) |
| :-- | :--: | :--: |
| **Sequential** (IVF/PQ scan) | **93.6 %** | 12 829 |
| **Random** (graph/HNSW walk) | **55.1 %** | 18 134 |

> Same algorithm, same data — **only the memory access *order* changes**, yet cycles rise **+41 %** and the row‑hit rate drops **38 points**. That is the whole thesis, in one controlled experiment, on a cycle‑accurate simulator.

> ⚠️ **On "PIM speed‑up."** Ramulator models the **DRAM path only** — it does *not* simulate a near‑memory compute unit, so this project does **not** measure an end‑to‑end host‑vs‑PIM speed‑up. The figures of **2.36× / 1.47×** that appear in `make demo` come from an *analytical* model (`toy_timing`) under **explicitly assumed** host/PIM bandwidths (8 vs 64 GB/s) and are **illustrative estimates, not measurements**. Treat the row‑hit/cycle numbers as the validated result; treat the speed‑up as a back‑of‑envelope projection pending a real near‑bank compute model.

**Which lever recovers the random case?** (real HBM2)

| Intervention | Row‑hit rate | Verdict |
| :-- | :--: | :-- |
| Random baseline | 55.1 % | the problem |
| Random **+ reordering** (window `W`≤256) | 56.2 % | ❌ no help — controller already reorders |
| Random **+ cluster layout** | **93.6 %** | ✅ full recovery (= sequential) |

**How much layout is enough?** Row‑hit vs cluster size `C` (real HBM2):

| `C` (vectors co‑located) | 1 | 4 | 16 | 32 | 64 |
| :-- | :--: | :--: | :--: | :--: | :--: |
| Row‑hit rate | 55.4 % | 87.6 % | **93.6 %** | 93.6 % | 93.6 % |

> Grouping just **16 co‑visited vectors** makes graph‑ANN read memory exactly as well as a sequential scan — a cheap, one‑time index‑build transformation.

---

## 🔎 Deeper results — a design rule and its limits

Three further sweeps on real HBM2 (`scripts/deep_experiments.sh`) sharpen the layout finding into something a real index‑builder can use.

**1. The threshold is a *byte budget*, not a vector count.** Sweeping cluster size `C` across vector dimensions, row‑hit always saturates where `dim × C ≈ 1 KB` — one DRAM row:

| dim \ `C` | 1 | 4 | 8 | 16 | 32 | 64 |
| :-- | :--: | :--: | :--: | :--: | :--: | :--: |
| **64 B** | 29.9 | 78.8 | 88.3 | **93.6** | 93.6 | 93.6 |
| **128 B** | 55.1 | 87.8 | **93.5** | 93.6 | 93.6 | 93.6 |
| **256 B** | 75.6 | **93.5** | 93.6 | 93.6 | 93.6 | 93.6 |

> This gives a predictive design rule: **`C* ≈ 1024 / (dim × dtype_bytes)`** — co‑locate ~1 KB of co‑visited data and locality is fully recovered at any dimension.

**2. Imperfect layouts degrade gracefully — but need ~90 % accuracy.** Row‑hit vs the fraction `Q` of correctly co‑located vectors (dim 128, `C`=16):

| `Q` | 0 % | 25 % | 50 % | 75 % | 90 % | 100 % |
| :-- | :--: | :--: | :--: | :--: | :--: | :--: |
| Row‑hit | 56.2 | 60.8 | 71.4 | 82.5 | 88.9 | 93.6 |

**3. The gain is contingent on an *open‑page* policy.** Under closed‑page auto‑precharge, sequential access collapses (93.6 % → 75.0 %) and even becomes *slower* than random — so the layout fix only pays off on open‑page controllers (the sensible default for bandwidth‑bound PIM):

| Policy | Sequential row‑hit | Random row‑hit |
| :-- | :--: | :--: |
| **Open page** | 93.6 % | 55.1 % |
| **Closed page** | 75.0 % | 54.7 % |

---

## 🔬 Follow‑up study: does a smart layout help on *real* data? (`sprint1/`)

The results above use a synthetic memory trace. The companion study in
[`sprint1/`](sprint1/) tests the layout idea on a **real HNSW index searching
real SIFT1M data**, comparing four layouts (random, community, BFS, and a
proposed *query‑aware* method) through the same cycle‑accurate simulator — with
a proper train/test split, so any gain reflects generalisation.

**Honest headline:** on real data, a **learned query‑aware layout does *not*
beat a simple BFS traversal‑order layout** — because on a real graph, the
neighbours you walk to are already the vectors read together, so BFS co‑locates
them for free. This is a **negative result with a clear mechanism**, and it
reinforces the byte‑budget finding above (layout gains are marginal at dim‑128
float32). Full write‑up: [`sprint1/docs/findings.md`](sprint1/docs/findings.md);
the picture that tells the story: `sprint1/fig_synth_vs_real.png`.

---

## 📂 Repository layout

```
Thesis-PIM-ANN/
├── PROJECT_OVERVIEW.md       # ← start here: plain-language tour of everything
├── src/                      # the main experiment (5 small C++ tools)
│   ├── ann_kernel.cpp        #   real ANN distance + top‑k (seq / rand order)
│   ├── gen_trace.cpp         #   emit a Ramulator LD/ST memory trace
│   ├── toy_timing.cpp        #   teaching‑size DRAM row‑buffer model
│   ├── reorder.cpp           #   access reordering (tested — does NOT help)
│   └── gen_layout.cpp        #   cluster‑ordered layout (the fix that works)
├── scripts/
│   ├── setup_ramulator.sh    #   build Ramulator 2.1 + run on real HBM2
│   ├── deep_experiments.sh   #   byte‑law + layout‑quality + policy sweeps
│   └── run_ann_ramulator.py  #   LoadStoreTrace + HBM2 config
├── doc/                      # the write‑ups
│   ├── pim_ann_ieee.pdf      #   IEEE conference paper (+ .tex, figures)
│   └── pim_ann_thesis.pdf    #   detailed from‑first‑principles report (+ .tex)
├── sprint1/                  # follow‑up: real‑HNSW layout study (negative result)
├── Makefile                  # build / demo / sweep / optsweep / layoutsweep
└── README.md
```

---

## ⚙️ Dependencies

**To run the core experiments (Part A)** — nothing but a compiler and Make:

| Tool | Version | Install |
| :-- | :-- | :-- |
| C++ compiler | C++20 (`g++ 11+` or `clang++ 15+`) | `sudo apt install g++`  ·  `sudo pacman -S gcc` |
| GNU Make | any | `sudo apt install make`  ·  `sudo pacman -S make` |

**To validate on real Ramulator (Part B)** — a few more, all standard:

| Tool | Version | Install |
| :-- | :-- | :-- |
| git | any | `sudo apt install git`  ·  `sudo pacman -S git` |
| CMake | ≥ 3.14 *(auto‑downloaded if missing)* | `sudo apt install cmake`  ·  `sudo pacman -S cmake` |
| Python + dev headers | 3.10+ | `sudo apt install python3-dev`  ·  `sudo pacman -S python` |

> `scripts/setup_ramulator.sh` checks all of these for you, fetches a prebuilt CMake if yours is missing, and pre‑clones Ramulator's dependencies for a robust offline build.

---

## 🚀 Part A — Reproduce the core results (just a compiler)

```bash
git clone https://github.com/senqx/Thesis-PIM-ANN.git
cd Thesis-PIM-ANN
make            # build the tools into ./bin
```

Then run any of the experiments:

```bash
make demo        # Experiment 1 & 2: sequential vs random  (the headline gap)
make sweep       # Experiment 3: shows pattern — not size — governs locality
make optsweep    # Experiment 4: reordering does NOT recover it
make layoutsweep # Experiment 5: cluster‑ordered layout fully recovers it
```

**Example output** (`make demo`):

```
=== traces/ann_seq.trace ===
  PIM   cycles=42240   hit-rate=99.2%   PIM speedup: 2.36x   (analytical est.)
=== traces/ann_rand.trace ===
  PIM   cycles=121680  hit-rate=50.7%   PIM speedup: 1.47x   (analytical est.)
```

`make sweep`, `make optsweep` and `make layoutsweep` write CSVs to `results/` that you can plot.

> **Note on the toy model (and the speed‑up numbers).** `toy_timing` models only the one DRAM effect that matters here — the **row buffer** — so its *absolute* numbers are illustrative. The **shape** (sequential ≫ random, and the recovery trend) is robust and is confirmed on real HBM2 in Part B. The `PIM speedup` it prints is an **analytical estimate** under assumed host/PIM bandwidths (8 vs 64 GB/s), **not** a measured near‑memory speed‑up; only the row‑hit and cycle behaviour is validated cycle‑accurately.

---

## 🔬 Part B — Validate on real Ramulator 2.1 (cycle‑accurate HBM2)

One command builds the simulator from source and replays the *same* traces through a real HBM2 timing model:

```bash
./scripts/setup_ramulator.sh
```

It will: ensure a C++20 compiler + CMake → clone & build Ramulator 2.1 →
generate the ANN traces → replay them on HBM2 → print **real** cycles,
row‑hit rate, latency and throughput for sequential and random.

Then, for the deeper design‑rule sweeps (byte budget, layout quality, page policy):

```bash
./scripts/deep_experiments.sh   # writes ~/deep_results.txt
```

> 💡 On a remote machine, run it inside `tmux` so a dropped connection doesn't kill the build:  `tmux new -s ram` … `./scripts/setup_ramulator.sh` … detach with `Ctrl‑b d`.

---

## 🧪 What each experiment shows

| Command | Research question | Finding |
| :-- | :-- | :-- |
| `make demo` | Does access **pattern** govern performance? | Yes — random costs +41 % cycles, −38 pts row‑hit |
| `make sweep` | Is it **pattern** or **dataset size**? | Pattern: hit‑rate is flat across a 32× size range |
| `make optsweep` | Does **reordering** recover it? | No — ~55 % → ~56 %, redundant with the controller |
| `make layoutsweep` | Does **layout** recover it? | Yes — fully, by cluster size `C`≈16 |
| `setup_ramulator.sh` | Do the ratios hold on **real** timing? | Yes — validated on cycle‑accurate HBM2 |
| `deep_experiments.sh` | What's the **design rule** and its limits? | ~1 KB byte budget; needs ~90 % layout accuracy; open‑page only |
| `sprint1/` (real HNSW) | Does a **learned layout** beat BFS on **real** data? | No — BFS is already strong; negative result with a mechanism |

---

## 📄 Papers

- **`doc/pim_ann_ieee.pdf`** — IEEE conference‑format paper with research questions, the proposed *locality‑aware graph layout*, the design rule, and the multi‑DPU parallelism analysis.
- **`doc/pim_ann_thesis.pdf`** — a longer, from‑first‑principles report (memory wall → PIM → ANN → DRAM → results), written so any technically literate reader can follow it. Both `.tex` sources are included.

---

## ✍️ Author

**senqx** — Master's thesis preparatory work, Computer Science / Computer Architecture (HPC).

## 📜 License

MIT — see `LICENSE`.
