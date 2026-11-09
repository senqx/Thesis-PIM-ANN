// Synthetic-corpus driver that emits all four layout traces for Ramulator.
// Mirror of run_sift.cpp but with a built-in clustered corpus, so you can get a
// cycle-accurate layout comparison with NO dataset download. Emits
// test_{random,bfs,community,query_aware}.ldst (held-out test queries) plus the
// honest inter-vector metric. Replay with scripts/replay_ramulator.sh test.
//
// Usage: run_synth [count] [trainQ] [testQ] [efSearch]

#include <algorithm>
#include <cstdint>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <random>
#include <string>
#include <vector>

#include "ann/hnsw_adapter.h"
#include "ann/trace_collector.h"
#include "layout/bfs_layout.h"
#include "layout/community_layout.h"
#include "layout/covisitation_model.h"
#include "layout/query_aware_layout.h"
#include "layout/random_layout.h"
#include "layout_metrics.h"
#include "memory/address_emitter.h"

namespace {

using namespace pimann;

std::vector<float> makeCorpus(
    uint32_t dim, uint64_t count, uint32_t clusters, std::mt19937& r_rng) {
  std::normal_distribution<float> jitter(0.0f, 0.15f);
  std::uniform_real_distribution<float> coord(-1.0f, 1.0f);
  std::vector<std::vector<float>> centroid(clusters, std::vector<float>(dim));
  for (auto& r_c : centroid) {
    for (float& r_x : r_c) {
      r_x = coord(r_rng);
    }
  }
  std::vector<float> data(count * dim);
  for (uint64_t i = 0; i < count; i++) {
    const auto& c = centroid[i % clusters];
    for (uint32_t d = 0; d < dim; d++) {
      data[i * dim + d] = c[d] + jitter(r_rng);
    }
  }
  return data;
}

AccessTrace collectRange(
    const HnswAdapter& adapter, const std::vector<float>& queries,
    uint32_t dim, uint32_t dtypeBytes, uint32_t k, uint64_t first,
    uint64_t last) {
  TraceCollector collector(dim, dtypeBytes);
  for (uint64_t q = first; q < last; q++) {
    collector.beginQuery(q);
    adapter.searchInstrumented(queries.data() + q * dim, k, collector);
  }
  return collector.trace();
}

void emit(
    const AccessTrace& trace, const MemoryLayout& layout,
    const std::string& path) {
  AddressPlan plan;
  AddressEmitter emitter(layout, plan);
  std::ofstream out(path);
  emitter.emit(trace, out);
}

}  // namespace

int main(int argc, char* argv[]) {
  const uint64_t count = argc > 1 ? std::stoull(argv[1]) : 20000;
  const uint64_t trainQ = argc > 2 ? std::stoull(argv[2]) : 400;
  const uint64_t testQ = argc > 3 ? std::stoull(argv[3]) : 200;
  const uint32_t ef = argc > 4 ? std::stoul(argv[4]) : 64;
  const uint32_t dim = 128;
  const uint32_t rowBytes = 2048;
  const uint32_t k = 10;

  std::mt19937 rng(42);
  std::cerr << "[synth] corpus " << count << " base, " << trainQ << " train + "
            << testQ << " test, dim " << dim << ", ef " << ef << "\n";
  const std::vector<float> base = makeCorpus(dim, count, 64, rng);
  const std::vector<float> queries = makeCorpus(dim, trainQ + testQ, 64, rng);

  HnswConfig config;
  config.dimension = dim;
  config.dtypeBytes = sizeof(float);
  config.m = 16;
  config.efSearch = ef;

  HnswAdapter adapter(config);
  std::cerr << "[synth] building HNSW index...\n";
  adapter.addVectors(base.data(), count);

  std::cerr << "[synth] learning co-visitation on train queries...\n";
  const AccessTrace trainTrace =
      collectRange(adapter, queries, dim, config.dtypeBytes, k, 0, trainQ);
  CoVisitationModel model;
  model.accumulate(trainTrace);
  model.finalize();

  std::cerr << "[synth] collecting held-out test traces...\n";
  const AccessTrace testTrace = collectRange(
      adapter, queries, dim, config.dtypeBytes, k, trainQ, trainQ + testQ);

  RandomLayout randomLayout(1);
  BfsLayout bfsLayout;
  CommunityLayout communityLayout;
  QueryAwareLayout queryLayout(model, rowBytes);
  randomLayout.build(adapter);
  bfsLayout.build(adapter);
  communityLayout.build(adapter);
  queryLayout.build(adapter);

  const uint32_t vectorBytes = dim * sizeof(float);
  auto report = [&](const char* name, const MemoryLayout& layout) {
    const LayoutMetrics m =
        computeMetrics(testTrace, layout, rowBytes, vectorBytes);
    std::cout << std::left << std::setw(13) << name << std::right
              << std::fixed << std::setprecision(3)
              << std::setw(12) << m.allBurstRowHit
              << std::setw(14) << m.interVectorRowHit
              << std::setw(14) << m.covisitColocation << "\n";
  };

  std::cout << "# synthetic real-HNSW layout benchmark (efSearch=" << ef
            << ")\n";
  std::cout << std::left << std::setw(13) << "layout" << std::right
            << std::setw(12) << "allBurst%" << std::setw(14) << "interVec%"
            << std::setw(14) << "coloc%" << "\n";
  report("random", randomLayout);
  report("bfs", bfsLayout);
  report("community", communityLayout);
  report("query_aware", queryLayout);

  emit(testTrace, randomLayout, "test_random.ldst");
  emit(testTrace, bfsLayout, "test_bfs.ldst");
  emit(testTrace, communityLayout, "test_community.ldst");
  emit(testTrace, queryLayout, "test_query_aware.ldst");
  std::cerr << "[synth] wrote test_{random,bfs,community,query_aware}.ldst\n";
  return 0;
}
