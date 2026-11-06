// gen_trace.cpp
// ---------------------------------------------------------------------------
// Emit a memory-access TRACE for the ANN kernel, in a format Ramulator can
// replay. We target Ramulator 2.1's `LoadStoreTrace` frontend, whose format is
// one record per line:
//
//       LD 0x<address>          (a memory read / load)
//       ST 0x<address>          (a memory write / store)
//
// The ANN distance-scan is read-only: for each candidate vector we LOAD it in
// 64-byte bursts (one cache line at a time). SEQUENTIAL visitation = IVF/PQ;
// RANDOM visitation = graph/HNSW-style traversal.
//
// SCOPE (read this before interpreting results): this is a CONTROLLED
// MICROBENCHMARK, not a real HNSW workload. The "random" pattern is a uniform
// permutation of vector reads -- a deliberate stand-in for graph traversal that
// isolates access *order* as the single variable. It does NOT model HNSW's
// data-dependent traversal, neighbour-list accesses, efSearch, or early
// termination. For memory traces from a REAL hnswlib index over real SIFT1M,
// see the sprint1/ study. This tool also only emits addresses; it does not run
// the distance arithmetic (that lives in ann_kernel.cpp).
//
// Default dtype is int8 (--dtype 1), so a 128-dim vector is 128 bytes (PQ-style),
// NOT a 512-byte float32 vector. Vector encoding affects the byte-budget rule,
// so it is printed to stderr on every run.
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

namespace {

[[noreturn]] void die(const std::string& msg) {
    fprintf(stderr, "[gen_trace] error: %s\n", msg.c_str());
    std::exit(1);
}

}  // namespace

int main(int argc, char** argv) {
    uint64_t num_vectors = 4096, dim = 128, dtype_bytes = 1, base = 0x100000, seed = 1;
    uint64_t burst = 64;                 // DRAM access granularity (cache line)
    std::string pattern = "seq";

    for (int i = 1; i < argc; i++) {
        std::string k = argv[i];
        auto next = [&](const char* flag) -> const char* {
            if (i + 1 >= argc) die(std::string("missing value for ") + flag);
            return argv[++i];
        };
        auto nn = [&](const char* flag) { return std::strtoull(next(flag), nullptr, 0); };
        if      (k == "--num_vectors") num_vectors = nn("--num_vectors");
        else if (k == "--dim")         dim         = nn("--dim");
        else if (k == "--dtype")       dtype_bytes = nn("--dtype");
        else if (k == "--base")        base        = nn("--base");
        else if (k == "--seed")        seed        = nn("--seed");
        else if (k == "--pattern")     pattern     = next("--pattern");
        else die("unknown argument: " + k);
    }

    // Input validation (reject values that would silently produce garbage).
    if (num_vectors == 0) die("--num_vectors must be > 0");
    if (dim == 0)         die("--dim must be > 0");
    if (dtype_bytes == 0) die("--dtype must be > 0");
    if (pattern != "seq" && pattern != "rand")
        die("--pattern must be 'seq' or 'rand' (got '" + pattern + "')");
    // Guard the multiplications against overflow (would wrap the address space).
    if (dim > UINT64_MAX / dtype_bytes) die("dim * dtype overflows");
    const uint64_t vec_bytes = dim * dtype_bytes;
    if (num_vectors > (UINT64_MAX - base) / vec_bytes)
        die("num_vectors * vec_bytes overflows the address space");

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
