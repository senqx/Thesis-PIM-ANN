#!/usr/bin/env bash
# =============================================================================
# deep_experiments.sh — run the deeper validation suite on real Ramulator.
# Prereqs: run from inside the Thesis-PIM-ANN repo AFTER ./scripts/setup_ramulator.sh
#          has built ramulator2/ (so ramulator2/libramulator.so exists).
# Produces: ~/deep_results.txt  (one tidy summary you can screenshot).
# VirtualBox note: slower in wall-clock, but cycle counts are identical to bare metal.
# =============================================================================
set -u
REPO="$PWD"
RAM="$REPO/ramulator2"
[ -f "$RAM/libramulator.so" ] || { echo "ERROR: build Ramulator first (./scripts/setup_ramulator.sh)"; exit 1; }
export PYTHONPATH="$RAM/python" LD_LIBRARY_PATH="$RAM"
OUT="$HOME/deep_results.txt"; : > "$OUT"
log(){ echo "$@" | tee -a "$OUT"; }

# ---- parameterized runner (row policy + dram preset selectable) -------------
cat > /tmp/run_param.py <<'PYEOF'
import sys, ramulator
trace, policy, dram = sys.argv[1], sys.argv[2], sys.argv[3]
try:
    fe = ramulator.frontend.LoadStoreTrace(clock_ratio=8, path=trace)
    if dram=="HBM3":
        # stock Ramulator 2.1 may not ship HBM3; try a couple preset spellings
        dev=None
        for org,tim in [("HBM3_8Gb","HBM3_6400MT"),("HBM3_8Gb","HBM3_6400Mbps")]:
            try: dev=ramulator.dram.HBM3(org_preset=org,timing_preset=tim); break
            except Exception: pass
        if dev is None: print("SKIP"); sys.exit(0)
    else:
        dev = ramulator.dram.HBM2(org_preset="HBM2_8Gb", timing_preset="HBM2_2000Mbps")
    if policy=="Close":
        rp=None
        for name in ("Close","Closed","ClosePage"):
            if hasattr(ramulator.row_policy,name):
                rp=getattr(ramulator.row_policy,name)(); break
        if rp is None: print("SKIP"); sys.exit(0)
    else:
        rp = ramulator.row_policy.Open()
    ctrl = ramulator.controller.GenericDDR(dram=dev, scheduler=ramulator.scheduler.FRFCFS(),
           refresh_manager=ramulator.refresh_manager.AllBank(), row_policy=rp,
           addr_mapper=ramulator.addr_mapper.RoBaRaCoCh())
    mem = ramulator.memory_system.GenericDRAM(clock_ratio=3, controllers=[ctrl],
          channel_mapper=ramulator.channel_mapper.CacheLineInterleave())
    sim = ramulator.Simulation(fe, mem); sim.run()
    cs = sim.stats["memory_system"]["controller"]
    if isinstance(cs,list): cs=cs[0]
    h,m,c = cs["read_row_hits"], cs["read_row_misses"], cs["read_row_conflicts"]
    tot=h+m+c; hr=100.0*h/tot if tot else 0
    print(f"{cs['cycles']},{round(hr,1)}")
except Exception as e:
    print("SKIP")
PYEOF
run(){ r=$(python3 /tmp/run_param.py "$1" "${2:-Open}" "${3:-HBM2}" 2>/dev/null); [ "$r" = "SKIP" ] && r=""; echo "$r"; }

# ---- embedded trace generators (compiled once) ------------------------------
mkdir -p /tmp/gens traces
cat > /tmp/gens/layout.cpp <<'EOF'
#include <cstdio>
#include <cstdint>
#include <cstdlib>
#include <string>
#include <vector>
#include <numeric>
#include <random>
#include <algorithm>
int main(int ac,char**av){uint64_t n=4096,dim=128,base=0x100000,seed=1,C=16,bu=64;
 for(int i=1;i<ac;i++){std::string k=av[i];auto nn=[&]{return std::strtoull(av[++i],0,0);};
 if(k=="--num_vectors")n=nn();else if(k=="--dim")dim=nn();else if(k=="--cluster")C=nn();else if(k=="--seed")seed=nn();}
 if(C<1)C=1;uint64_t vb=dim;std::mt19937 r(seed);uint64_t nc=(n+C-1)/C;std::vector<uint64_t>cl(nc);
 std::iota(cl.begin(),cl.end(),0ULL);std::shuffle(cl.begin(),cl.end(),r);
 for(uint64_t c:cl)for(uint64_t j=0;j<C;j++){uint64_t v=c*C+j;if(v>=n)break;uint64_t a=base+v*vb;
 for(uint64_t o=0;o<vb;o+=bu)printf("LD 0x%llx\n",(unsigned long long)(a+o));}return 0;}
EOF
cat > /tmp/gens/base.cpp <<'EOF'
#include <cstdio>
#include <cstdint>
#include <cstdlib>
#include <string>
#include <vector>
#include <numeric>
#include <random>
#include <algorithm>
int main(int ac,char**av){uint64_t n=4096,dim=128,base=0x100000,seed=1,bu=64;std::string pat="seq";
 for(int i=1;i<ac;i++){std::string k=av[i];auto nn=[&]{return std::strtoull(av[++i],0,0);};
 if(k=="--num_vectors")n=nn();else if(k=="--dim")dim=nn();else if(k=="--seed")seed=nn();else if(k=="--pattern")pat=av[++i];}
 uint64_t vb=dim;std::vector<uint64_t>o(n);std::iota(o.begin(),o.end(),0ULL);
 if(pat=="rand"){std::mt19937 r(seed);std::shuffle(o.begin(),o.end(),r);}
 for(uint64_t v:o){uint64_t a=base+v*vb;for(uint64_t of=0;of<vb;of+=bu)printf("LD 0x%llx\n",(unsigned long long)(a+of));}return 0;}
EOF
cat > /tmp/gens/layoutq.cpp <<'EOF'
#include <cstdio>
#include <cstdint>
#include <cstdlib>
#include <string>
#include <vector>
#include <numeric>
#include <random>
#include <algorithm>
int main(int ac,char**av){uint64_t n=4096,dim=128,base=0x100000,seed=1,C=16,bu=64;int q=100;
 for(int i=1;i<ac;i++){std::string k=av[i];auto nn=[&]{return std::strtoull(av[++i],0,0);};
 if(k=="--num_vectors")n=nn();else if(k=="--dim")dim=nn();else if(k=="--cluster")C=nn();else if(k=="--quality")q=(int)nn();else if(k=="--seed")seed=nn();}
 uint64_t vb=dim;std::mt19937 r(seed);std::vector<uint64_t>slot(n);std::iota(slot.begin(),slot.end(),0ULL);
 std::uniform_int_distribution<uint64_t>pick(0,n-1);std::uniform_int_distribution<int>pct(1,100);
 for(uint64_t v=0;v<n;v++)if(pct(r)>q)slot[v]=pick(r);
 uint64_t nc=(n+C-1)/C;std::vector<uint64_t>cl(nc);std::iota(cl.begin(),cl.end(),0ULL);std::shuffle(cl.begin(),cl.end(),r);
 for(uint64_t c:cl)for(uint64_t j=0;j<C;j++){uint64_t v=c*C+j;if(v>=n)break;uint64_t a=base+slot[v]*vb;
 for(uint64_t o=0;o<vb;o+=bu)printf("LD 0x%llx\n",(unsigned long long)(a+o));}return 0;}
EOF
for g in layout base layoutq; do g++ -std=c++20 -O2 /tmp/gens/$g.cpp -o /tmp/gens/$g 2>/dev/null; done
GL=/tmp/gens/layout; GB=/tmp/gens/base; GQ=/tmp/gens/layoutq

log "================= DEEP EXPERIMENTS (real Ramulator) ================="
log ""
# ---- EXP1: dimension x cluster law (C_sat * vector_bytes ~ const?) ----------
log "### EXP1: row-hit vs (dim, cluster)  [looking for a byte-threshold law]"
log "dim \\ C      1     4     8    16    32    64"
for D in 64 128 256; do
  line="dim=$D "
  for C in 1 4 8 16 32 64; do
    $GL --num_vectors 4096 --dim $D --cluster $C > traces/x.trace 2>/dev/null
    hr=$(run traces/x.trace Open HBM2 | cut -d, -f2)
    line="$line $(printf '%5s' $hr)"
  done
  log "$line"
done
log ""
# ---- EXP2: imperfect layout quality ----------------------------------------
log "### EXP2: row-hit vs layout quality Q% (dim128 C16)"
log "Q%:   0    25    50    75    90   100"
line="hit: "
for Q in 0 25 50 75 90 100; do
  $GQ --num_vectors 4096 --dim 128 --cluster 16 --quality $Q > traces/x.trace 2>/dev/null
  hr=$(run traces/x.trace Open HBM2 | cut -d, -f2); line="$line $(printf '%5s' $hr)"
done
log "$line"
log ""
# ---- EXP3: row policy robustness (Open vs Close) ---------------------------
log "### EXP3: core gap under Open vs Close row policy"
$GB --num_vectors 4096 --dim 128 --pattern seq  > traces/seq.trace 2>/dev/null
$GB --num_vectors 4096 --dim 128 --pattern rand > traces/rnd.trace 2>/dev/null
for P in Open Close; do
  s=$(run traces/seq.trace $P HBM2); r=$(run traces/rnd.trace $P HBM2)
  log "  policy=$P  SEQ hit=$(echo $s|cut -d, -f2)% cyc=$(echo $s|cut -d, -f1)   RAND hit=$(echo $r|cut -d, -f2)% cyc=$(echo $r|cut -d, -f1)"
done
log ""
# ---- EXP4: HBM3 generation (if preset exists) ------------------------------
log "### EXP4: core gap on HBM3 (if available)"
s=$(run traces/seq.trace Open HBM3); r=$(run traces/rnd.trace Open HBM3)
if [ -n "$s" ] && [ -n "$r" ]; then
  log "  HBM3  SEQ hit=$(echo $s|cut -d, -f2)% cyc=$(echo $s|cut -d, -f1)   RAND hit=$(echo $r|cut -d, -f2)% cyc=$(echo $r|cut -d, -f1)"
else
  log "  (HBM3 preset not available in this Ramulator build — skipped)"
fi
log ""
log "================= DONE — results saved to $OUT ================="
cat "$OUT"
