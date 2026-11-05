// gen_layout.cpp
// ---------------------------------------------------------------------------
// Cluster-ordered LAYOUT trace generator for graph-ANN on PIM.
//
// This models the proposed fix. A graph/HNSW query visits different regions of
// the index in an unpredictable (random) order, but if vectors that are visited
// together are placed CONTIGUOUSLY in memory, those accesses fall in the same
// DRAM rows and become row hits.
//
// We therefore:
//   * group the n candidate vectors into clusters of size C;
//   * visit the clusters in RANDOM order (as graph traversal does);
//   * but read each cluster's vectors CONTIGUOUSLY (cluster-ordered layout).
//
// Sweeping C shows how much co-location is needed:
//   C = 1   -> every vector alone  = pure random access (no layout benefit)
//   C large -> big contiguous runs = approaches a sequential scan
// On real HBM2 the row-hit rate recovers to the sequential ceiling by C ~ 16.
//
// Output: Ramulator LoadStoreTrace format (one "LD 0x<addr>" per 64-byte burst),
// identical to gen_trace.cpp, so it plugs straight into run_ann_ramulator.py.
//
// Build:  g++ -std=c++20 -O2 gen_layout.cpp -o gen_layout
// Run:    ./gen_layout --num_vectors 4096 --dim 128 --cluster 16 > layout.trace
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
    uint64_t cluster = 16, burst = 64;   // cluster = vectors co-located per DRAM-friendly block

    for (int i = 1; i < argc; i++) {
        std::string k = argv[i];
        auto nn = [&]{ return std::strtoull(argv[++i], 0, 0); };
        if      (k == "--num_vectors") num_vectors = nn();
        else if (k == "--dim")         dim         = nn();
        else if (k == "--dtype")       dtype_bytes = nn();
        else if (k == "--cluster")     cluster     = nn();
        else if (k == "--base")        base        = nn();
        else if (k == "--seed")        seed        = nn();
    }
    if (cluster < 1) cluster = 1;
    const uint64_t vec_bytes = dim * dtype_bytes;

    // cluster ids in random visitation order; vectors within a cluster are contiguous
    const uint64_t n_clusters = (num_vectors + cluster - 1) / cluster;
    std::vector<uint64_t> cl(n_clusters);
    std::iota(cl.begin(), cl.end(), 0ULL);
    std::mt19937 rng(seed);
    std::shuffle(cl.begin(), cl.end(), rng);

    uint64_t loads = 0, bytes = 0;
    for (uint64_t c : cl) {
        for (uint64_t j = 0; j < cluster; j++) {
            uint64_t v = c * cluster + j;
            if (v >= num_vectors) break;
            uint64_t addr = base + v * vec_bytes;        // contiguous placement
            for (uint64_t off = 0; off < vec_bytes; off += burst) {
                printf("LD 0x%llx\n", (unsigned long long)(addr + off));
                loads++; bytes += burst;
            }
        }
    }
    fprintf(stderr,
        "[gen_layout] vectors=%llu dim=%llu cluster=%llu  -> %llu LD records (%.2f MB)\n",
        (unsigned long long)num_vectors, (unsigned long long)dim,
        (unsigned long long)cluster, (unsigned long long)loads, bytes/(1024.0*1024.0));
    return 0;
}
