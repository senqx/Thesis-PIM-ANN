#!/usr/bin/env bash
# multiseed_sift.sh - run the four-layout comparison on a REAL .fvecs dataset
# across N seeds and report mean / stddev / 95% CI per layout (honest
# inter-vector row-hit %). Addresses the "single-seed, no CI on real data"
# review point. Each seed re-shuffles the train/test query split, so the CI
# captures generalisation variance, not just layout-RNG noise.
#
# Build first (from sprint1/):  make run_sift_multiseed
# Usage: ./scripts/multiseed_sift.sh <base.fvecs> <query.fvecs> \
#          [NSEEDS] [maxBase] [trainQ] [testQ] [ef]
set -u
BASE="${1:?need base.fvecs}"; QUERY="${2:?need query.fvecs}"
NSEEDS="${3:-10}"; MAXBASE="${4:-100000}"
TRAINQ="${5:-500}"; TESTQ="${6:-200}"; EF="${7:-64}"
BIN=./run_sift_multiseed
[ -x "$BIN" ] || { echo "build first: make run_sift_multiseed"; exit 1; }

OUT=multiseed_sift_results.csv
echo "seed,random,community,query_aware,bfs" > "$OUT"
echo "running $NSEEDS seeds on $BASE (maxBase=$MAXBASE ef=$EF)..." >&2
for s in $(seq 1 "$NSEEDS"); do
  "$BIN" "$BASE" "$QUERY" "$s" "$MAXBASE" "$TRAINQ" "$TESTQ" "$EF" >> "$OUT"
  echo "  seed $s done" >&2
done

echo >&2
awk -F, '
NR==1 { next }
{ for (i=2;i<=5;i++){ sum[i]+=$i; sq[i]+=$i*$i } n++ }
END {
  split("random community query_aware bfs", name, " ");
  printf "%-14s %8s %8s %11s %18s\n", "layout","mean","stddev","95%CI(+-)","95%CI_interval";
  for (i=2;i<=5;i++){
    m=sum[i]/n;
    var=(n>1)?(sq[i]-n*m*m)/(n-1):0; sd=sqrt(var>0?var:0);
    ci=(n>1)?1.96*sd/sqrt(n):0;
    printf "%-14s %8.4f %8.4f %11.4f   [%7.4f, %7.4f]\n",
           name[i-1], m, sd, ci, m-ci, m+ci;
  }
  printf "\n(n=%d seeds; honest inter-vector row-hit %%. If BFS and query_aware\n", n;
  printf " 95%% CIs do NOT overlap, their ordering is statistically distinguishable.)\n";
}' "$OUT"
