// ann_kernel.cpp
// ---------------------------------------------------------------------------
// The REAL computation: the inner loop of IVF/PQ Approximate Nearest Neighbor
// (ANN) search. This is ordinary C++ you would actually run and later
// *instrument* to feed a PIM simulator.
//
// What it does: given a query vector and a batch of candidate vectors stored
// contiguously, compute the (squared L2) distance from the query to every
// candidate and keep the top-k smallest. The distance math is cheap; the cost
// is STREAMING the candidate array out of memory -> a memory-bound kernel,
// which is exactly why it is a good PIM target.
//
// Two access patterns are provided, because their contrast is the whole point:
//   SEQUENTIAL : scan candidates in storage order  (IVF / PQ cell scan)
//   RANDOM     : visit candidates in a shuffled order (mimics graph / HNSW
//                pointer-chasing, the hard, still-open PIM case)
//
// Build:  g++ -std=c++20 -O2 ann_kernel.cpp -o ann_kernel
// Run:    ./ann_kernel --num_vectors 4096 --dim 128 --pattern seq --topk 10
// ---------------------------------------------------------------------------
#include <cstdio>
#include <cstdint>
#include <cstdlib>
#include <cstring>
#include <string>
#include <vector>
#include <random>
#include <algorithm>
#include <limits>

struct Args {
    uint64_t num_vectors = 4096;   // candidates in this IVF cell / batch
    uint64_t dim         = 128;    // vector dimensionality (128 ~ SIFT)
    std::string pattern  = "seq";  // "seq" or "rand"
    uint64_t topk        = 10;
    uint64_t seed        = 1;
};

static Args parse(int argc, char** argv) {
    Args a;
    for (int i = 1; i < argc; i++) {
        std::string k = argv[i];
        auto v = [&]{ return std::string(argv[++i]); };
        if      (k == "--num_vectors") a.num_vectors = std::strtoull(v().c_str(),0,0);
        else if (k == "--dim")         a.dim         = std::strtoull(v().c_str(),0,0);
        else if (k == "--pattern")     a.pattern     = v();
        else if (k == "--topk")        a.topk        = std::strtoull(v().c_str(),0,0);
        else if (k == "--seed")        a.seed        = std::strtoull(v().c_str(),0,0);
    }
    return a;
}

int main(int argc, char** argv) {
    Args a = parse(argc, argv);

    // --- set up data (int8 quantized vectors, PQ-style) ---
    std::mt19937 rng(a.seed);
    std::uniform_int_distribution<int> d(-128, 127);
    std::vector<int8_t> data(a.num_vectors * a.dim);
    for (auto& x : data) x = (int8_t)d(rng);
    std::vector<int8_t> query(a.dim);
    for (auto& x : query) x = (int8_t)d(rng);

    // visitation order: sequential or shuffled (graph-traversal mimic)
    std::vector<uint64_t> order(a.num_vectors);
    for (uint64_t i = 0; i < a.num_vectors; i++) order[i] = i;
    if (a.pattern == "rand") std::shuffle(order.begin(), order.end(), rng);

    // --- the memory-bound inner loop: distance to every candidate ---
    using Pair = std::pair<int64_t,uint64_t>;   // (distance, id)
    std::vector<Pair> best;
    best.reserve(a.topk + 1);
    for (uint64_t idx = 0; idx < a.num_vectors; idx++) {
        uint64_t v = order[idx];
        const int8_t* cand = &data[v * a.dim];
        int64_t dist = 0;
        for (uint64_t j = 0; j < a.dim; j++) {       // squared L2 distance
            int64_t diff = (int64_t)query[j] - (int64_t)cand[j];
            dist += diff * diff;
        }
        // maintain top-k (small k -> cheap)
        if (best.size() < a.topk) { best.push_back({dist, v}); std::push_heap(best.begin(), best.end()); }
        else if (dist < best.front().first) {
            std::pop_heap(best.begin(), best.end()); best.back() = {dist, v}; std::push_heap(best.begin(), best.end());
        }
    }
    std::sort_heap(best.begin(), best.end());

    printf("ANN kernel: %llu vectors, dim=%llu, pattern=%s, top-%llu\n",
           (unsigned long long)a.num_vectors, (unsigned long long)a.dim,
           a.pattern.c_str(), (unsigned long long)a.topk);
    printf("nearest ids (dist): ");
    for (auto& p : best) printf("%llu(%lld) ", (unsigned long long)p.second, (long long)p.first);
    printf("\n");
    return 0;
}
