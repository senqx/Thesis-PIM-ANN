// run_sift_multiseed.cpp
// ---------------------------------------------------------------------------
// Multi-seed confidence intervals for the four-layout comparison on a REAL
// dataset (SIFT1M .fvecs). Addresses the reviewer's statistical-validity point:
// the single-seed real-data margins are small, so we need CIs.
//
// On a REAL corpus the base vectors are fixed, so the only legitimate per-seed
// randomness is (i) the train/test QUERY split (we shuffle the query pool and
// re-partition each seed) and (ii) the Random and Community layout seeds. BFS
// and QueryAware are deterministic given the split; their per-seed variation
// therefore comes entirely from which queries train the co-visitation model and
// which are held out for scoring -- exactly the generalisation question.
//
// Output (one CSV line per seed): seed,random,community,query_aware,bfs
//   values are the honest inter-vector row-hit % on the held-out test queries.
//
// Usage: run_sift_multiseed <base.fvecs> <query.fvecs> <seed>
//                           [maxBase] [trainQ] [testQ] [ef]
// Aggregate many seeds with scripts/multiseed_sift.sh.
// ---------------------------------------------------------------------------
#include <algorithm>
#include <cstdint>
#include <iostream>
#include <numeric>
#include <random>
#include <string>
#include <vector>

#include "ann/fvecs_loader.h"
#include "ann/hnsw_adapter.h"
#include "ann/trace_collector.h"
#include "layout/bfs_layout.h"
#include "layout/community_layout.h"
#include "layout/covisitation_model.h"
#include "layout/query_aware_layout.h"
#include "layout/random_layout.h"
#include "layout_metrics.h"

namespace {
using namespace pimann;

// Collect a trace over an explicit list of query indices (so we can shuffle).
AccessTrace collectIdx(const HnswAdapter& adapter,
                       const std::vector<float>& queries, uint32_t dim,
                       uint32_t k, const std::vector<uint64_t>& idx,
                       uint64_t first, uint64_t last) {
  TraceCollector collector(dim, sizeof(float));
  for (uint64_t i = first; i < last; i++) {
    const uint64_t q = idx[i];
    collector.beginQuery(q);
    adapter.searchInstrumented(queries.data() + q * dim, k, collector);
  }
  return collector.trace();
}
}  // namespace

int main(int argc, char* argv[]) {
  if (argc < 4) {
    std::cerr << "usage: " << argv[0]
              << " <base.fvecs> <query.fvecs> <seed>"
                 " [maxBase] [trainQ] [testQ] [ef]\n";
    return 1;
  }
  const std::string basePath = argv[1];
  const std::string queryPath = argv[2];
  const uint64_t seed = std::stoull(argv[3]);
  const uint64_t maxBase = argc > 4 ? std::stoull(argv[4]) : 100000;
  const uint64_t trainQ = argc > 5 ? std::stoull(argv[5]) : 500;
  const uint64_t testQ = argc > 6 ? std::stoull(argv[6]) : 200;
  const uint32_t ef = argc > 7 ? std::stoul(argv[7]) : 64;
  const uint32_t k = 10;
  const uint32_t rowBytes = 2048;

  const VecData b = loadFvecs(basePath, maxBase);
  const VecData q = loadFvecs(queryPath, trainQ + testQ);
  if (b.dim != q.dim) {
    std::cerr << "dim mismatch\n";
    return 1;
  }
  const uint32_t dim = b.dim;

  HnswConfig config;
  config.dimension = dim;
  config.dtypeBytes = sizeof(float);
  config.m = 16;
  config.efSearch = ef;
  HnswAdapter adapter(config);
  adapter.addVectors(b.data.data(), b.count);

  // Per-seed train/test split: shuffle the query pool with this seed.
  const uint64_t nq = q.count;
  std::vector<uint64_t> idx(nq);
  std::iota(idx.begin(), idx.end(), 0ULL);
  std::mt19937_64 rng(seed);
  std::shuffle(idx.begin(), idx.end(), rng);

  const AccessTrace trainTrace =
      collectIdx(adapter, q.data, dim, k, idx, 0, trainQ);
  CoVisitationModel model;
  model.accumulate(trainTrace);
  model.finalize();
  const AccessTrace testTrace =
      collectIdx(adapter, q.data, dim, k, idx, trainQ, trainQ + testQ);

  // Seed the stochastic layouts; BFS/QueryAware are deterministic given split.
  RandomLayout randomLayout(seed);
  BfsLayout bfsLayout;
  CommunityLayout communityLayout(20, seed);
  QueryAwareLayout queryLayout(model, rowBytes);
  randomLayout.build(adapter);
  bfsLayout.build(adapter);
  communityLayout.build(adapter);
  queryLayout.build(adapter);

  const uint32_t vectorBytes = dim * sizeof(float);
  auto iv = [&](const MemoryLayout& L) {
    return computeMetrics(testTrace, L, rowBytes, vectorBytes).interVectorRowHit;
  };
  std::cout << seed << ',' << iv(randomLayout) << ',' << iv(communityLayout)
            << ',' << iv(queryLayout) << ',' << iv(bfsLayout) << "\n";
  return 0;
}
