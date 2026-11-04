// gen_trace.cpp
// ---------------------------------------------------------------------------
// Emit a memory-access TRACE for the ANN kernel, in a format Ramulator can
// replay. We target Ramulator 2.1's `LoadStoreTrace` frontend, whose format is
// one record per line:
//
//       LD 0x<address>          (a memory read / load)
//       ST 0x<address>          (a memory write / store)
//
// (Ramulator's `SimpleO3` frontend additionally wants an instruction-count
//  "bubble" between accesses; LoadStoreTrace is the simplest and is what we use.
//  Section README: LoadStoreTrace "replays a flat-address trace with LD and ST
//  records".)
//
// The ANN distance-scan is read-only: for each candidate vector we LOAD it in
// 64-byte bursts (one cache line at a time). SEQUENTIAL visitation = IVF/PQ;
// RANDOM visitation = graph/HNSW-style traversal.
//
// Build:  g++ -std=c++20 -O2 gen_trace.cpp -o gen_trace
// Run:    ./gen_trace --num_vectors 4096 --dim 128 --pattern seq > traces/ann_seq.trace
// ---------------------------------------------------------------------------
#include <cstdio>
#include <cstdint>
#include <cstdlib>
#include <string>
#include <vector>
#include <numeric>
#include <random>
#include <algorithm>

int main(int argc, char** argv) {
    uint64_t num_vectors = 4096, dim = 128, dtype_bytes = 1, base = 0x100000, seed = 1;
    uint64_t burst = 64;                 // DRAM access granularity (cache line)
    std::string pattern = "seq";

    for (int i = 1; i < argc; i++) {
        std::string k = argv[i];
        auto nn = [&]{ return std::strtoull(argv[++i],0,0); };
        if      (k == "--num_vectors") num_vectors = nn();
        else if (k == "--dim")         dim         = nn();
        else if (k == "--dtype")       dtype_bytes = nn();
        else if (k == "--base")        base        = nn();
        else if (k == "--seed")        seed        = nn();
        else if (k == "--pattern")     pattern     = argv[++i];
    }

    const uint64_t vec_bytes = dim * dtype_bytes;

    std::vector<uint64_t> order(num_vectors);
    std::iota(order.begin(), order.end(), 0ULL);
    if (pattern == "rand") { std::mt19937 rng(seed); std::shuffle(order.begin(), order.end(), rng); }

    uint64_t loads = 0, bytes = 0;
    for (uint64_t v : order) {
        uint64_t addr = base + v * vec_bytes;
        for (uint64_t off = 0; off < vec_bytes; off += burst) {
            printf("LD 0x%llx\n", (unsigned long long)(addr + off));
            loads++; bytes += burst;
        }
    }

    fprintf(stderr,
        "[gen_trace] pattern=%s vectors=%llu dim=%llu dtype=%lluB vec_bytes=%llu\n"
        "[gen_trace] emitted %llu LD records (%lluB bursts) = %.2f MB\n",
        pattern.c_str(), (unsigned long long)num_vectors, (unsigned long long)dim,
        (unsigned long long)dtype_bytes, (unsigned long long)vec_bytes,
        (unsigned long long)loads, (unsigned long long)burst, bytes/(1024.0*1024.0));
    return 0;
}
