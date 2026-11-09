#!/usr/bin/env bash
# multiseed.sh — run the four-layout comparison across N seeds and report
# mean / stddev / 95% CI per layout, so the BFS-vs-query-aware ordering has
# statistical weight (addresses the "single-seed, no CI" review point).
#
# Build first:  (from sprint1/)  g++ -std=c++20 -O2 -I src -isystem third_party \
#                 src/run_multiseed.cpp <CORE .cpp> -o run_multiseed
# Or:           make run_multiseed   (if a target is added)
#
# Usage: ./scripts/multiseed.sh [NSEEDS] [count] [trainQ] [testQ] [ef]
set -u
NSEEDS="${1:-10}"
COUNT="${2:-15000}"; TRAINQ="${3:-300}"; TESTQ="${4:-150}"; EF="${5:-64}"
BIN=./run_multiseed
[ -x "$BIN" ] || { echo "build run_multiseed first (see header)"; exit 1; }

OUT=multiseed_results.csv
echo "seed,random,community,query_aware,bfs" > "$OUT"
echo "running $NSEEDS seeds (count=$COUNT ef=$EF)..." >&2
for s in $(seq 1 "$NSEEDS"); do
  "$BIN" "$s" "$COUNT" "$TRAINQ" "$TESTQ" "$EF" >> "$OUT"
  echo "  seed $s done" >&2
done

# Aggregate with awk: mean, sample stddev, 95% CI half-width (t~1.96 for large N;
# for small N this is approximate — reported as such).
echo >&2
awk -F, '
NR==1 { next }
{ for (i=2;i<=5;i++){ sum[i]+=$i; sq[i]+=$i*$i } n++ }
END {
  split("random community query_aware bfs", name, " ");
  printf "%-14s %8s %8s %10s\n", "layout", "mean", "stddev", "95%CI(+-)";
  for (i=2;i<=5;i++){
    m=sum[i]/n;
    var=(n>1)?(sq[i]-n*m*m)/(n-1):0; sd=sqrt(var>0?var:0);
    ci=(n>1)?1.96*sd/sqrt(n):0;
    printf "%-14s %8.4f %8.4f %10.4f\n", name[i-1], m, sd, ci;
  }
  printf "\n(n=%d seeds; inter-vector row-hit %%. BFS vs query-aware: compare\n", n;
  printf " means relative to the CI half-widths -- overlapping CIs = not distinguishable.)\n";
}' "$OUT"
echo >&2
echo "raw rows in $OUT" >&2
