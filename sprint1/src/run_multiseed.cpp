// run_multiseed.cpp
// ---------------------------------------------------------------------------
// One seeded run of the four-layout comparison, for statistical aggregation.
//
// Review feedback (correctly) noted that the Sprint-1 comparisons were
// single-seed: with a ~0.45% cycle spread "within noise", we cannot claim BFS
// beats query-aware without a noise distribution. This driver makes the whole
// pipeline a function of one --seed: the synthetic corpus, the query set, and
// the random-layout permutation all derive from it. Run it across many seeds
// (see scripts/multiseed.sh) and aggregate mean / stddev / 95% CI, so the
// BFS-vs-query-aware ordering can be reported WITH error bars.
//
// Output (one line, CSV): seed,random,community,query_aware,bfs
//   -- the honest inter-vector row-hit % for each layout on that seed.
//
// Usage: run_multiseed <seed> [count] [trainQ] [testQ] [ef]
// ---------------------------------------------------------------------------
#include <cstdint>
#include <iostream>
#include <random>
#include <vector>

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

std::vector<float> makeCorpus(
    uint32_t dim, uint64_t count, uint32_t clusters, std::mt19937& r_rng) {
  std::normal_distribution<float> jitter(0.0f, 0.15f);
  std::uniform_real_distribution<float> coord(-1.0f, 1.0f);
  std::vector<std::vector<float>> centroid(clusters, std::vector<float>(dim));
  for (auto& r_c : centroid)
    for (float& r_x : r_c) r_x = coord(r_rng);
  std::vector<float> data(count * dim);
  for (uint64_t i = 0; i < count; i++) {
    const auto& c = centroid[i % clusters];
    for (uint32_t d = 0; d < dim; d++)
      data[i * dim + d] = c[d] + jitter(r_rng);
  }
  return data;
}

AccessTrace collect(
    const HnswAdapter& a, const std::vector<float>& q, uint32_t dim,
    uint32_t dtype, uint32_t k, uint64_t first, uint64_t last) {
  TraceCollector c(dim, dtype);
  for (uint64_t i = first; i < last; i++) {
    c.beginQuery(i);
    a.searchInstrumented(q.data() + i * dim, k, c);
  }
  return c.trace();
}
}  // namespace

int main(int argc, char* argv[]) {
  if (argc < 2) {
    std::cerr << "usage: " << argv[0]
              << " <seed> [count] [trainQ] [testQ] [ef]\n";
    return 1;
  }
  const uint64_t seed   = std::stoull(argv[1]);
  const uint64_t count  = argc > 2 ? std::stoull(argv[2]) : 15000;
  const uint64_t trainQ = argc > 3 ? std::stoull(argv[3]) : 300;
  const uint64_t testQ  = argc > 4 ? std::stoull(argv[4]) : 150;
  const uint32_t ef     = argc > 5 ? std::stoul(argv[5]) : 64;
  const uint32_t dim = 128, rowBytes = 2048, k = 10;

  // Everything derives from `seed`: corpus data, query set, random layout.
  std::mt19937 rng(seed);
  const std::vector<float> base = makeCorpus(dim, count, 64, rng);
  const std::vector<float> queries = makeCorpus(dim, trainQ + testQ, 64, rng);

  HnswConfig cfg;
  cfg.dimension = dim; cfg.dtypeBytes = sizeof(float);
  cfg.m = 16; cfg.efSearch = ef;
  HnswAdapter adapter(cfg);
  adapter.addVectors(base.data(), count);

  const AccessTrace trainTrace =
      collect(adapter, queries, dim, cfg.dtypeBytes, k, 0, trainQ);
  CoVisitationModel model;
  model.accumulate(trainTrace);
  model.finalize();
  const AccessTrace testTrace =
      collect(adapter, queries, dim, cfg.dtypeBytes, k, trainQ, trainQ + testQ);

  RandomLayout randomL(seed);          // seed-dependent permutation
  BfsLayout bfsL;
  CommunityLayout communityL(20, seed);  // seed-dependent label-prop
  QueryAwareLayout queryL(model, rowBytes);
  randomL.build(adapter); bfsL.build(adapter);
  communityL.build(adapter); queryL.build(adapter);

  const uint32_t vb = dim * sizeof(float);
  auto iv = [&](const MemoryLayout& L) {
    return computeMetrics(testTrace, L, rowBytes, vb).interVectorRowHit;
  };
  // CSV: seed,random,community,query_aware,bfs
  std::cout << seed << ',' << iv(randomL) << ',' << iv(communityL) << ','
            << iv(queryL) << ',' << iv(bfsL) << "\n";
  return 0;
}
