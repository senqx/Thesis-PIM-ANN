// reorder.cpp
// ---------------------------------------------------------------------------
// Locality recovery for a random (graph/HNSW) memory trace.
//
// Reads an LD/ST trace on stdin and sorts the accesses *within sliding windows
// of size W* by address, writing the reordered trace to stdout. This is an
// idealised model of two real techniques that improve DRAM locality:
//   - query batching: the memory controller reorders across many pending
//     requests to cluster same-row accesses;
//   - a deeper controller reorder window (FR-FCFS looking further ahead).
//
// W = 1   -> trace unchanged (pure random, the worst case).
// W large -> approaches a fully sorted (sequential) trace, the best case.
// Sweeping W interpolates between the two and shows how much of the lost
// row-buffer locality a given amount of reordering recovers.
//
// Build:  g++ -std=c++20 -O2 reorder.cpp -o reorder
// Use:    ./reorder 128 < rand.trace > rand_w128.trace
// ---------------------------------------------------------------------------
#include <cstdio>
#include <cstdint>
#include <cstdlib>
#include <string>
#include <vector>
#include <algorithm>
#include <iostream>

int main(int argc, char** argv) {
    if (argc < 2) { std::fprintf(stderr, "usage: %s <window> < in.trace > out.trace\n", argv[0]); return 1; }
    // Validate the window argument is a positive integer (reject "abc", "-5", "0").
    char* end = nullptr;
    const unsigned long long w_in = std::strtoull(argv[1], &end, 0);
    if (end == argv[1] || *end != '\0' || w_in == 0) {
        std::fprintf(stderr, "[reorder] error: <window> must be a positive integer (got '%s')\n", argv[1]);
        return 1;
    }
    const size_t W = (size_t)w_in;

    // read all records: (op, addr, original_line)
    struct Rec { uint64_t addr; std::string line; };
    std::vector<Rec> recs;
    std::string line;
    while (std::getline(std::cin, line)) {
        if (line.empty()) continue;
        // line is "LD 0x...." / "ST 0x...."
        size_t sp = line.find(' ');
        uint64_t a = (sp == std::string::npos) ? 0 : std::strtoull(line.c_str() + sp + 1, nullptr, 0);
        recs.push_back({a, line});
    }

    // sort each window of W consecutive records by address (cluster same-row)
    for (size_t i = 0; i < recs.size(); i += W) {
        size_t j = std::min(recs.size(), i + W);
        std::stable_sort(recs.begin() + i, recs.begin() + j,
                         [](const Rec& x, const Rec& y) { return x.addr < y.addr; });
    }

    for (const auto& r : recs) std::puts(r.line.c_str());
    return 0;
}
