#!/usr/bin/env python3
# Run our ANN memory trace through REAL Ramulator 2.1 (cycle-accurate HBM2).
#
# This reports *DRAM-locality* metrics only (row-hit rate, cycles, latency,
# throughput). It does NOT model a near-memory compute unit, so it does not
# produce a host-vs-PIM application speedup; any such figure elsewhere in this
# repo is an analytical estimate (see src/toy_timing.cpp), not a measurement.
#
# Usage:
#   PYTHONPATH=<ramulator>/python LD_LIBRARY_PATH=<ramulator> \
#     python3 run_ann_ramulator.py <trace_file> [--csv]
#
# DRAM geometry is fixed entirely by the Ramulator org/timing presets below
# (HBM2_8Gb @ 2.0 Gbps, RoBaRaCoCh mapping, cache-line channel interleave) --
# NOT by any external row-size constant.
import sys
import ramulator

args = [a for a in sys.argv[1:] if not a.startswith("--")]
as_csv = "--csv" in sys.argv
trace = args[0] if args else "ann_seq.trace"

# Frontend: replay a flat LD/ST address trace (our gen_trace output).
frontend = ramulator.frontend.LoadStoreTrace(clock_ratio=8, path=trace)

# DRAM: HBM2, 8Gb per channel, 2.0 Gbps. Open row policy = row-buffer effect.
hbm2 = ramulator.dram.HBM2(org_preset="HBM2_8Gb", timing_preset="HBM2_2000Mbps")
ctrl = ramulator.controller.GenericDDR(
    dram=hbm2,
    scheduler=ramulator.scheduler.FRFCFS(),
    refresh_manager=ramulator.refresh_manager.AllBank(),
    row_policy=ramulator.row_policy.Open(),
    addr_mapper=ramulator.addr_mapper.RoBaRaCoCh(),
)
mem = ramulator.memory_system.GenericDRAM(
    clock_ratio=3,
    controllers=[ctrl],
    channel_mapper=ramulator.channel_mapper.CacheLineInterleave(),
)

sim = ramulator.Simulation(frontend, mem)
sim.run()

cs = sim.stats["memory_system"]["controller"]
if isinstance(cs, list):
    cs = cs[0]
hits = cs["read_row_hits"]
miss = cs["read_row_misses"]
conf = cs["read_row_conflicts"]
total = hits + miss + conf
hitrate = 100.0 * hits / total if total else 0.0

if as_csv:
    # cycles,row_hit_pct  (header is emitted by the caller)
    print(f"{cs['cycles']},{round(hitrate, 1)}")
else:
    print("TRACE:", trace)
    print("  cycles           =", cs["cycles"])
    print("  avg_read_latency =", round(cs["avg_read_latency"], 2), "cycles")
    print("  read_throughput  =", round(cs["read_throughput_MBps"], 1), "MB/s")
    print("  row hit/miss/conf=", hits, "/", miss, "/", conf)
    print("  ROW-HIT RATE     =", round(hitrate, 1), "%")
    print("  num_read_reqs    =", cs["num_read_reqs"])
