# pim-ann-demo — a minimal, working trace-driven PIM experiment

A small, self-contained project that demonstrates the **trace-driven simulation flow** used by Ramulator, applied to the **ANN (Approximate Nearest Neighbor) distance-scan** kernel at the heart of vector search. It runs today with nothing but a C++ compiler, and it is structured so you can swap the teaching-size timing model for the **real Ramulator 2.1** when your VM is ready.

The project proves, in one experiment, the core thesis insight:

> A **sequential** ANN scan (IVF / PQ) is memory-bandwidth-bound and PIM-friendly.
> A **random** ANN traversal (graph / HNSW) loses the DRAM row-buffer advantage — which is exactly why graph-ANN-on-PIM is the open research gap.

---

## 0. What's in here

```
pim-ann-demo/
├── Makefile                 # build + demo + sweep targets
├── README.md                # this file
├── src/
│   ├── ann_kernel.cpp       # the REAL computation (IVF/PQ distance + top-k)
│   ├── gen_trace.cpp        # emits a Ramulator-format LD/ST memory trace
│   └── toy_timing.cpp       # teaching-size cycle model (stand-in for Ramulator)
├── traces/                  # generated .trace files (created on run)
└── results/                 # sweep CSV (created on run)
```

Three tiny tools, one idea each:
- **`ann_kernel`** — the actual C++ you would run and later instrument. Computes squared-L2 distance from a query to every candidate vector and keeps the top-k. Supports `--pattern seq` (IVF/PQ scan order) and `--pattern rand` (graph/HNSW traversal order). Both return the *same* nearest neighbors; only the memory access *order* differs.
- **`gen_trace`** — writes the memory-access trace the kernel performs, in **Ramulator 2.1 `LoadStoreTrace` format** (`LD 0x<addr>` / `ST 0x<addr>`, one per line).
- **`toy_timing`** — replays a trace through a simple DRAM **row-buffer** timing model and reports cycles + achieved bandwidth for a HOST path and a near-bank PIM path. This is a *stand-in* so you see the flow before installing Ramulator.

> ⚠️ **Honesty note:** `toy_timing`'s absolute numbers are illustrative, not validated nanoseconds. The cycle costs are hand-chosen so the *behavior and ratios* match real DRAM. Use Ramulator (Part B) for trustworthy absolute timing. The *shape* of the result (seq ≫ rand) is robust and is the point.

---

## Part A — Run the demo right now (only needs g++)

Requirements: a C++20 compiler (`g++ 11+` or `clang++ 15+`) and `make`.

```bash
cd pim-ann-demo

# build the three tools
make

# run the headline demo: build two traces (seq + rand) and time them
make demo
```

Expected output (your absolute numbers may differ slightly; the ratio is the point):

```
=== traces/ann_seq.trace ===
  HOST  cycles=99584   hits=8128 misses=64  hit-rate=99.2%  achieved=5.3 B/cyc
  PIM   cycles=42240   hits=8128 misses=64  hit-rate=99.2%  achieved=12.4 B/cyc
  PIM speedup: 2.36x

=== traces/ann_rand.trace ===
  HOST  cycles=179024  hits=4156 misses=4036 hit-rate=50.7%  achieved=2.9 B/cyc
  PIM   cycles=121680  hits=4156 misses=4036 hit-rate=50.7%  achieved=4.3 B/cyc
  PIM speedup: 1.47x
```

Read it: the **sequential** scan is almost all row-hits (99%) and PIM wins big; the **random** traversal is half row-misses (50%) and the PIM advantage shrinks. That gap *is* your research motivation.

### Sweep (your first experiment figure)

```bash
make sweep          # varies vector count for seq and rand, writes results/sweep.csv
```

`results/sweep.csv` has columns `pattern,num_vectors,host_cycles,pim_cycles,speedup,hit_rate` — ready to plot (seq stays ~2.36×, rand stays ~1.47×, independent of size, which is itself a finding about the access *pattern* being what matters).

### Run the real kernel directly

```bash
./bin/ann_kernel --num_vectors 4096 --dim 128 --pattern seq  --topk 10
./bin/ann_kernel --num_vectors 4096 --dim 128 --pattern rand --topk 10   # same neighbors, different access order
```

---

## Part B — Do it "for real" with Ramulator 2.1

Ramulator is the cycle-accurate DRAM simulator from ETH Zürich's SAFARI group. Here you replace `toy_timing` with Ramulator, feeding it the **same trace** `gen_trace` already produces.

### B.1 Install prerequisites (Ubuntu/Debian; adapt for Arch)

```bash
# Debian/Ubuntu
sudo apt-get update
sudo apt-get install -y g++-12 cmake python3 python3-pip python3-venv git

# Arch
sudo pacman -S --needed gcc cmake python git
```
Ramulator 2.1 needs a **C++20 compiler** and **CMake ≥ 3.14**. `yaml-cpp` and `fmt` are auto-fetched by CMake — you do *not* install them manually.

### B.2 Clone and build

```bash
git clone https://github.com/CMU-SAFARI/ramulator2.git
cd ramulator2
mkdir -p build && cd build
cmake ..
make -j
cd ..
# sanity check: run the bundled example
python3 examples/example_config.py      # should print simulation statistics
```
This builds `libramulator.so` in the repo root and a `ramulator2` executable.

### B.3 Feed it OUR trace

`gen_trace` already emits Ramulator's `LoadStoreTrace` format, so generate traces and point Ramulator's `LoadStoreTrace` frontend at them. Create a config (Python API, mirrors `examples/example_config.py` but swaps the frontend):

```python
# run_ann.py  —  put this in the ramulator2 repo root
import ramulator

frontend = ramulator.frontend.LoadStoreTrace(
    trace="../pim-ann-demo/traces/ann_seq.trace",   # <-- our trace
)
hbm = ramulator.dram.HBM2(org_preset="HBM2_8Gb", timing_preset="HBM2_2Gbps")
ctrl = ramulator.controller.GenericDDR(
    dram=hbm,
    scheduler=ramulator.scheduler.FRFCFS(),
    refresh_manager=ramulator.refresh_manager.AllBank(),
    row_policy=ramulator.row_policy.Open(),           # row-buffer policy — the effect our toy modeled
    addr_mapper=ramulator.addr_mapper.RoBaRaCoCh(),
)
mem = ramulator.memory_system.GenericDRAM(clock_ratio=3, controllers=[ctrl],
        channel_mapper=ramulator.channel_mapper.CacheLineInterleave())
sim = ramulator.Simulation(frontend, mem)
sim.run()
print(sim.stats["memory_system"]["controller"])      # real cycles, row hits/misses, etc.
```

```bash
# generate the trace first
cd ../pim-ann-demo && make && ./bin/gen_trace --num_vectors 4096 --dim 128 --pattern seq > traces/ann_seq.trace
cd ../ramulator2 && PYTHONPATH=python python3 run_ann.py
```

> Check the exact frontend arg names in `src/ramulator/frontend/impl/memory_trace/` (the API evolves between releases). If `LoadStoreTrace` wants a different keyword, the README §"Frontends" lists them. The concept is unchanged: a flat `LD/ST` address trace in, cycle-accurate DRAM stats out.

Now you have **real, trustworthy** HBM timing for the identical kernel — swap `ann_seq.trace` ↔ `ann_rand.trace` to reproduce the seq-vs-rand contrast with validated numbers.

---

## Part C — How to run an arbitrary C program on it (the general recipe)

Our `gen_trace` hand-models the access pattern. For an *arbitrary* C/C++ program you instead **record its real accesses**. Two routes:

1. **Ramulator-PIM (ZSim frontend)** — the dedicated PIM framework. You annotate the hot region of your C code:
   ```c
   zsim_PIM_function_begin();
   ann_search(query, candidates, n);   // your real function
   zsim_PIM_function_end();
   ```
   Run it under ZSim, which records two traces — *filtered* (what the host CPU sees after caches) and *unfiltered* (every access, what a PIM core sees) — then replay them through Ramulator. This is the route that actually executes real programs and compares host-vs-PIM. Cost: ZSim is an older, heavier dependency (Intel Pin, scons) that takes effort to build.

2. **Any tracer → LD/ST** — simpler for a thesis: capture memory accesses with a lightweight tool (e.g. an Intel Pin pintool, Valgrind/Lackey, or DynamoRIO) and convert them to `LD 0x..` / `ST 0x..` lines. Then feed Ramulator exactly as in Part B. This keeps you on the clean Ramulator 2.1 codebase.

**For graph-ANN specifically** (the open gap): traversal is *data-dependent* — which node you visit next depends on computed distances — so a single static trace can't capture it faithfully. Options: (a) generate a trace **per query** from a real HNSW run, or (b) extend Ramulator with a small active-traversal model. That modeling tension is itself a contribution.

---

## Where this maps onto the thesis

- `ann_kernel.cpp` → the workload (IVF/PQ today; graph/HNSW is the open extension).
- `gen_trace.cpp` → how real accesses reach the simulator (replace with ZSim/Pin for arbitrary code).
- `toy_timing.cpp` → **replace with Ramulator 2.1** for validated timing.
- `make sweep` → the skeleton of your first experiment: vary a parameter, measure PIM speedup, plot.

Next experiment to try once Ramulator is up: reproduce the seq-vs-rand gap with real HBM2 timing, then push on the *rand* case — that is where graph-ANN-on-PIM research lives.
