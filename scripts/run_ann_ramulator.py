#!/usr/bin/env python3
# Run our ANN memory trace through REAL Ramulator 2.1 (cycle-accurate HBM2).
# Usage: PYTHONPATH=<ramulator>/python LD_LIBRARY_PATH=<ramulator> \
#        python3 run_ann_ramulator.py <trace_file>
import sys
import ramulator

trace = sys.argv[1] if len(sys.argv) > 1 else "ann_seq.trace"

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

stats = sim.stats
cs = stats["memory_system"]["controller"]
if isinstance(cs, list):
    cs = cs[0]
cs = stats["memory_system"]["controller"]
if isinstance(cs, list):
    cs = cs[0]
hits = cs["read_row_hits"]; miss = cs["read_row_misses"]; conf = cs["read_row_conflicts"]
total = hits + miss + conf
hitrate = 100.0 * hits / total if total else 0.0
print("TRACE:", trace)
print("  cycles           =", cs["cycles"])
print("  avg_read_latency =", round(cs["avg_read_latency"], 2), "cycles")
print("  read_throughput  =", round(cs["read_throughput_MBps"], 1), "MB/s")
print("  row hit/miss/conf=", hits, "/", miss, "/", conf)
print("  ROW-HIT RATE     =", round(hitrate, 1), "%")
print("  num_read_reqs    =", cs["num_read_reqs"])
