#!/usr/bin/env bash
# =============================================================================
# replay_ramulator.sh - cycle-accurate row-hit for each layout's emitted trace.
#
# Replays the sprint-1 *.ldst traces (random / bfs / community / query_aware)
# through the SAME Ramulator 2.1 HBM2 config the main thesis used
# (HBM2_8Gb @ 2000Mbps, FR-FCFS, Open row policy, RoBaRaCoCh), so the layout
# comparison is on identical cycle-accurate ground.
#
# Prereq: the main repo's ramulator2/ is built (libramulator.so present). Point
# RAM at it, or run this from a checkout that sits beside the main repo.
#
# Usage:
#   RAM=/path/to/Thesis-PIM-ANN/ramulator2 ./scripts/replay_ramulator.sh [prefix]
#   (prefix defaults to "sift_test"; use "test" for the synthetic driver output)
# =============================================================================
set -u
PREFIX="${1:-sift_test}"
RAM="${RAM:-$PWD/../Thesis-PIM-ANN/ramulator2}"
[ -f "$RAM/libramulator.so" ] || {
  echo "ERROR: libramulator.so not found under RAM=$RAM"
  echo "Set RAM to the built ramulator2/ dir from the main thesis repo."
  exit 1
}
export PYTHONPATH="$RAM/python" LD_LIBRARY_PATH="$RAM"

cat > /tmp/replay_one.py <<'PY'
import sys, ramulator
trace = sys.argv[1]
fe = ramulator.frontend.LoadStoreTrace(clock_ratio=8, path=trace)
dev = ramulator.dram.HBM2(org_preset="HBM2_8Gb", timing_preset="HBM2_2000Mbps")
ctrl = ramulator.controller.GenericDDR(
    dram=dev, scheduler=ramulator.scheduler.FRFCFS(),
    refresh_manager=ramulator.refresh_manager.AllBank(),
    row_policy=ramulator.row_policy.Open(),
    addr_mapper=ramulator.addr_mapper.RoBaRaCoCh())
mem = ramulator.memory_system.GenericDRAM(
    clock_ratio=3, controllers=[ctrl],
    channel_mapper=ramulator.channel_mapper.CacheLineInterleave())
sim = ramulator.Simulation(fe, mem); sim.run()
cs = sim.stats["memory_system"]["controller"]
if isinstance(cs, list): cs = cs[0]
h, m, c = cs["read_row_hits"], cs["read_row_misses"], cs["read_row_conflicts"]
tot = h + m + c
hr = 100.0 * h / tot if tot else 0.0
print(f"{cs['cycles']},{round(hr,2)},{cs['avg_read_latency']}")
PY

echo "layout,cycles,row_hit_pct,avg_read_latency"
for lay in random bfs community query_aware; do
  f="${PREFIX}_${lay}.ldst"
  [ -f "$f" ] || { echo "$lay,MISSING,,"; continue; }
  out=$(python3 /tmp/replay_one.py "$f" 2>/dev/null)
  echo "$lay,$out"
done
