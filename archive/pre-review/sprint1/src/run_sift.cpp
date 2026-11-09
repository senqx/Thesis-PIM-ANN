// Real-dataset driver: load SIFT1M (or any .fvecs corpus + query set), build a
// real HNSW index, learn the co-visitation model on a TRAIN query split, then
// emit held-out TEST traces under each layout for Ramulator and report the
// honest inter-vector locality metric.
//
// Usage:
//   run_sift <base.fvecs> <query.fvecs> [maxBase] [trainQ] [testQ] [efSearch]
//
// SIFT1M: base = sift_base.fvecs (1e6 x 128), query = sift_query.fvecs
// (1e4 x 128). Start with maxBase ~100000 for a quick first pass.

#include <algorithm>
#include <cstdint>
#include <fstream>
#include <iomanip>
#include <iostream>
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
#include "memory/address_emitter.h"
#include "metrics/recall_evaluator.h"

namespace {

using namespace pimann;

AccessTrace collectRange(
    const HnswAdapter& adapter, const VecData& queries, uint32_t dim,
    uint32_t dtypeBytes, uint32_t k, uint64_t first, uint64_t last) {
  TraceCollector collector(dim, dtypeBytes);
  for (uint64_t q = first; q < last; q++) {
    collector.beginQuery(q);
    adapter.searchInstrumented(
        queries.data.data() + q * dim, k, collector);
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
  if (argc < 3) {
    std::cerr << "usage: " << argv[0]
              << " <base.fvecs> <query.fvecs> [maxBase] [trainQ] [testQ] [ef]\n";
    return 1;
  }
  const std::string basePath = argv[1];
  const std::string queryPath = argv[2];
  const uint64_t maxBase = argc > 3 ? std::stoull(argv[3]) : 100000;
  const uint64_t trainQ = argc > 4 ? std::stoull(argv[4]) : 500;
  const uint64_t testQ = argc > 5 ? std::stoull(argv[5]) : 200;
  const uint32_t ef = argc > 6 ? std::stoul(argv[6]) : 64;
  const uint32_t rowBytes = 2048;
  const uint32_t k = 10;

  std::cerr << "[sift] loading base from " << basePath << " ...\n";
  const VecData base = loadFvecs(basePath, maxBase);
  std::cerr << "[sift] loading queries from " << queryPath << " ...\n";
  const VecData queries = loadFvecs(queryPath, trainQ + testQ);
  if (base.dim != queries.dim) {
    std::cerr << "dimension mismatch: base " << base.dim << " vs query "
              << queries.dim << "\n";
    return 1;
  }
  const uint32_t dim = base.dim;
  std::cerr << "[sift] base " << base.count << " x " << dim << ", queries "
            << queries.count << "\n";

  HnswConfig config;
  config.dimension = dim;
  config.dtypeBytes = sizeof(float);
  config.m = 16;
  config.efSearch = ef;

  HnswAdapter adapter(config);
  std::cerr << "[sift] building HNSW index (M=16, efSearch=" << ef << ")...\n";
  adapter.addVectors(base.data.data(), base.count);

  std::cerr << "[sift] learning co-visitation on " << trainQ
            << " train queries...\n";
  const AccessTrace trainTrace =
      collectRange(adapter, queries, dim, config.dtypeBytes, k, 0, trainQ);
  CoVisitationModel model;
  model.accumulate(trainTrace);
  model.finalize();

  std::cerr << "[sift] collecting " << testQ << " held-out test traces...\n";
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

  std::cout << "# SIFT real-HNSW layout benchmark (efSearch=" << ef << ")\n";
  std::cout << std::left << std::setw(13) << "layout" << std::right
            << std::setw(12) << "allBurst%" << std::setw(14) << "interVec%"
            << std::setw(14) << "coloc%" << "\n";
  report("random", randomLayout);
  report("bfs", bfsLayout);
  report("community", communityLayout);
  report("query_aware", queryLayout);

  // Emit held-out test traces for cycle-accurate replay.
  emit(testTrace, randomLayout, "sift_test_random.ldst");
  emit(testTrace, bfsLayout, "sift_test_bfs.ldst");
  emit(testTrace, communityLayout, "sift_test_community.ldst");
  emit(testTrace, queryLayout, "sift_test_query_aware.ldst");
  std::cerr << "[sift] wrote sift_test_{random,bfs,community,query_aware}.ldst\n";
  return 0;
}
