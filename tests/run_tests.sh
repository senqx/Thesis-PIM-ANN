#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# Automated tests for the root ANN/PIM microbenchmark tools.
# Checks: correct output on valid input, rejection of bad input (no crashes /
# no silent garbage), and determinism. Builds the tools first.
#
# Run:  ./tests/run_tests.sh      (from the repo root)
# Exit: 0 if all pass, 1 otherwise. Used by CI (.github/workflows/ci.yml).
# ---------------------------------------------------------------------------
set -u
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
BIN=bin
PASS=0; FAIL=0
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

ok()   { printf "  \033[32mPASS\033[0m %s\n" "$1"; PASS=$((PASS+1)); }
bad()  { printf "  \033[31mFAIL\033[0m %s\n" "$1"; FAIL=$((FAIL+1)); }

# expect_ok   <desc> <cmd...>        : command must exit 0
# expect_fail <desc> <cmd...>        : command must exit non-zero (clean reject)
expect_ok()   { local d="$1"; shift; if "$@" >/dev/null 2>&1; then ok "$d"; else bad "$d (expected success)"; fi; }
expect_fail() { local d="$1"; shift; if "$@" >/dev/null 2>&1; then bad "$d (expected failure, got success)"; else ok "$d"; fi; }

echo "== building tools =="
make all >/dev/null 2>&1 || { echo "BUILD FAILED"; exit 1; }

echo "== gen_trace =="
expect_ok   "gen_trace seq valid"            ./$BIN/gen_trace --num_vectors 256 --dim 128 --pattern seq
expect_ok   "gen_trace rand valid"           ./$BIN/gen_trace --num_vectors 256 --dim 128 --pattern rand
expect_fail "gen_trace rejects dim 0"        ./$BIN/gen_trace --dim 0
expect_fail "gen_trace rejects num_vectors 0" ./$BIN/gen_trace --num_vectors 0
expect_fail "gen_trace rejects bad pattern"  ./$BIN/gen_trace --pattern bogus
expect_fail "gen_trace rejects missing value" ./$BIN/gen_trace --dim
expect_fail "gen_trace rejects unknown flag" ./$BIN/gen_trace --nope 1
# correct record count: 256 vectors * (128*1 bytes / 64 burst) = 256*2 = 512 LD lines
n=$(./$BIN/gen_trace --num_vectors 256 --dim 128 --pattern seq 2>/dev/null | wc -l)
[ "$n" -eq 512 ] && ok "gen_trace emits 512 records" || bad "gen_trace record count ($n != 512)"
# determinism: same seed -> identical rand trace
a=$(./$BIN/gen_trace --num_vectors 256 --dim 128 --pattern rand --seed 7 2>/dev/null | md5sum)
b=$(./$BIN/gen_trace --num_vectors 256 --dim 128 --pattern rand --seed 7 2>/dev/null | md5sum)
[ "$a" = "$b" ] && ok "gen_trace rand is deterministic (same seed)" || bad "gen_trace rand not deterministic"

echo "== gen_layout =="
expect_ok   "gen_layout valid"               ./$BIN/gen_layout --num_vectors 256 --dim 128 --cluster 16
expect_fail "gen_layout rejects cluster 0"   ./$BIN/gen_layout --cluster 0
expect_fail "gen_layout rejects dim 0"       ./$BIN/gen_layout --dim 0
# C=1 (every vector alone) must emit the same record COUNT as a full scan
nl=$(./$BIN/gen_layout --num_vectors 256 --dim 128 --cluster 1 2>/dev/null | wc -l)
[ "$nl" -eq 512 ] && ok "gen_layout emits 512 records" || bad "gen_layout record count ($nl != 512)"

echo "== ann_kernel =="
expect_ok   "ann_kernel valid"               ./$BIN/ann_kernel --num_vectors 100 --dim 16 --topk 5
expect_fail "ann_kernel rejects topk 0"      ./$BIN/ann_kernel --topk 0
expect_fail "ann_kernel rejects dim 0"       ./$BIN/ann_kernel --dim 0
expect_fail "ann_kernel rejects bad pattern" ./$BIN/ann_kernel --pattern bogus
# seq and rand must return the SAME top-k set (order of visitation != result)
s=$(./$BIN/ann_kernel --num_vectors 500 --dim 32 --topk 10 --pattern seq  --seed 3 2>/dev/null | tail -1)
r=$(./$BIN/ann_kernel --num_vectors 500 --dim 32 --topk 10 --pattern rand --seed 3 2>/dev/null | tail -1)
# normalise: extract sorted id list
sids=$(echo "$s" | grep -o '[0-9]*(' | tr -d '(' | sort -n | tr '\n' ' ')
rids=$(echo "$r" | grep -o '[0-9]*(' | tr -d '(' | sort -n | tr '\n' ' ')
[ "$sids" = "$rids" ] && ok "ann_kernel seq/rand give same top-k (order-invariant)" || bad "ann_kernel seq/rand differ"

echo "== reorder =="
./$BIN/gen_trace --num_vectors 256 --dim 128 --pattern rand > "$TMP/r.trace" 2>/dev/null
expect_ok   "reorder valid window"           bash -c "./$BIN/reorder 16 < '$TMP/r.trace' > /dev/null"
expect_fail "reorder rejects non-numeric"    bash -c "echo 'LD 0x1' | ./$BIN/reorder abc"
expect_fail "reorder rejects window 0"       bash -c "echo 'LD 0x1' | ./$BIN/reorder 0"
# reorder preserves record count
inn=$(wc -l < "$TMP/r.trace"); outn=$(./$BIN/reorder 16 < "$TMP/r.trace" 2>/dev/null | wc -l)
[ "$inn" -eq "$outn" ] && ok "reorder preserves record count" || bad "reorder changed count ($inn != $outn)"

echo "== toy_timing =="
./$BIN/gen_trace --num_vectors 256 --dim 128 --pattern seq > "$TMP/s.trace" 2>/dev/null
expect_ok   "toy_timing valid trace"         ./$BIN/toy_timing "$TMP/s.trace"
expect_fail "toy_timing rejects empty trace" ./$BIN/toy_timing "$TMP/empty.trace"
: > "$TMP/empty.trace"
expect_fail "toy_timing empty -> no nan"     ./$BIN/toy_timing "$TMP/empty.trace"
expect_fail "toy_timing missing file arg"    ./$BIN/toy_timing
# seq must have a higher row-hit rate than rand (the core claim, qualitatively)
./$BIN/gen_trace --num_vectors 4096 --dim 128 --pattern rand > "$TMP/rand.trace" 2>/dev/null
hs=$(./$BIN/toy_timing "$TMP/s.trace"    --csv 2>/dev/null | cut -d, -f5)
hr=$(./$BIN/toy_timing "$TMP/rand.trace" --csv 2>/dev/null | cut -d, -f5)
awk "BEGIN{exit !($hs > $hr)}" && ok "toy_timing: seq hit-rate ($hs) > rand ($hr)" || bad "toy_timing seq not > rand ($hs vs $hr)"

echo
echo "==================================================="
printf "  RESULT: %d passed, %d failed\n" "$PASS" "$FAIL"
echo "==================================================="
[ "$FAIL" -eq 0 ]
