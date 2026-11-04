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

## 📌 The one‑sentence idea

> **Approximate Nearest Neighbour (ANN) search is memory‑bound, so it is a natural Processing‑in‑Memory (PIM) target — but *how* it reads memory decides whether PIM helps.**
> *Cluster‑based* ANN (IVF/PQ) reads memory **sequentially** and loves PIM. *Graph‑based* ANN (HNSW) reads it **randomly**, destroying DRAM row‑buffer locality — which is exactly why graph‑ANN‑on‑PIM is an open problem.

This repo **measures that gap** on a real cycle‑accurate simulator, then shows it is **partly recoverable** by reordering, and analyses **multi‑DPU parallelism**.

---

## 🎯 Headline results

All numbers below are produced by the code in this repo. The core ratios are reproduced on **real HBM2 timing (Ramulator 2.1)**.

| Access pattern | DRAM row‑hit rate | Cycles | PIM speed‑up |
| :-- | :--: | :--: | :--: |
| **Sequential** (IVF/PQ scan) | **93.6 %** | 12 829 | **2.36×** |
| **Random** (graph/HNSW walk) | **55.1 %** | 18 134 | **1.47×** |

> Same algorithm, same data — **only the memory access *order* changes**, yet cycles rise **+41 %** and the row‑hit rate drops **38 points**. That is the whole thesis, in one controlled experiment.

**Recovering the random case** (reordering / query batching, window `W`):

| `W` (reorder window) | 1 (random) | 64 | 128 | 256 | *(seq ceiling)* |
| :-- | :--: | :--: | :--: | :--: | :--: |
| Row‑hit rate | 50.7 % | 60.2 % | 67.7 % | **78.0 %** | *99.2 %* |

---

## 📂 Repository layout

```
Thesis-PIM-ANN/
├── src/                      # the experiment (4 small C++ tools)
│   ├── ann_kernel.cpp        #   real ANN distance + top‑k (seq / rand order)
│   ├── gen_trace.cpp         #   emit a Ramulator LD/ST memory trace
│   ├── toy_timing.cpp        #   teaching‑size DRAM row‑buffer model
│   └── reorder.cpp           #   locality‑recovery (windowed reordering)
├── scripts/
│   ├── setup_ramulator.sh    #   build Ramulator 2.1 + run on real HBM2
│   └── run_ann_ramulator.py  #   LoadStoreTrace + HBM2 config
├── doc/                      # the write‑ups
│   ├── pim_ann_ieee.pdf      #   IEEE conference paper (+ .tex, figures)
│   └── pim_ann_thesis.pdf    #   detailed from‑first‑principles report (+ .tex)
├── Makefile                  # build / demo / sweep / optsweep
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
make            # build the 4 tools into ./bin
```

Then run any of the three experiments:

```bash
make demo       # Experiment 1 & 2: sequential vs random  (the headline gap)
make sweep      # Experiment 3: shows pattern — not size — governs locality
make optsweep   # Experiment 4: locality recovery vs reorder window W
```

**Example output** (`make demo`):

```
=== traces/ann_seq.trace ===
  PIM   cycles=42240   hit-rate=99.2%   PIM speedup: 2.36x
=== traces/ann_rand.trace ===
  PIM   cycles=121680  hit-rate=50.7%   PIM speedup: 1.47x
```

`make sweep` and `make optsweep` write CSVs to `results/` that you can plot.

> **Note on the toy model.** `toy_timing` models only the one DRAM effect that matters here — the **row buffer** — so its *absolute* numbers are illustrative. The **shape** (sequential ≫ random, and the recovery trend) is robust and is confirmed on real HBM2 in Part B.

---

## 🔬 Part B — Validate on real Ramulator 2.1 (cycle‑accurate HBM2)

One command builds the simulator from source and replays the *same* traces through a real HBM2 timing model:

```bash
./scripts/setup_ramulator.sh
```

It will: ensure a C++20 compiler + CMake → clone & build Ramulator 2.1 →
generate the ANN traces → replay them on HBM2 → print **real** cycles,
row‑hit rate, latency and throughput for sequential and random.

> 💡 On a remote machine, run it inside `tmux` so a dropped connection doesn't kill the build:  `tmux new -s ram` … `./scripts/setup_ramulator.sh` … detach with `Ctrl‑b d`.

---

## 🧪 What each experiment shows

| Command | Research question | Finding |
| :-- | :-- | :-- |
| `make demo` | Does access **pattern** govern performance? | Yes — random costs +41 % cycles, −38 pts row‑hit |
| `make sweep` | Is it **pattern** or **dataset size**? | Pattern: hit‑rate is flat across a 32× size range |
| `make optsweep` | Can the random penalty be **recovered**? | Yes, partly — 50.7 % → 78.0 % row‑hit via reordering |
| `setup_ramulator.sh` | Do the ratios hold on **real** timing? | Yes — validated on cycle‑accurate HBM2 |

---

## 📄 Papers

- **`doc/pim_ann_ieee.pdf`** — IEEE conference‑format paper with research questions, the proposed *locality‑aware graph layout*, and the multi‑DPU parallelism analysis.
- **`doc/pim_ann_thesis.pdf`** — a longer, from‑first‑principles report (memory wall → PIM → ANN → DRAM → results), written so any technically literate reader can follow it. Both `.tex` sources are included.

---

## ✍️ Author

**Artashes Atanesyan** — Master's thesis preparatory work, Computer Science / Computer Architecture (HPC).

## 📜 License

MIT — see `LICENSE`.
