// Byte-budget stress test: does the layout advantage grow when vectors are
// SMALLER (so more fit per DRAM row)?
//
// Motivation. The main thesis found a byte-budget law: locality saturates when
// ~1 DRAM row (2 KB) of co-visited data is co-located. At dim 128 float32 a
// vector is 512 B, so only ~4 fit per row - a tiny co-location budget, and the
// sprint-1 real-SIFT result showed layout barely helps there. Product
// Quantization / int8 storage shrinks a vector to 128 B, so ~16 fit per row.
// The law predicts layout should matter MORE with that larger budget. This
// driver tests exactly that, sweeping the stored dtype in {float32, int8}.
//
// Modeling note. HNSW's access *pattern* (which nodes, in what order) is
// unchanged by PQ/int8 - compression changes a vector's byte footprint, not
// which candidates the search visits. So we keep the real float HNSW traversal
// and only vary the per-vector byte span used by the layout and the row-hit
// accounting. This isolates the byte-budget effect cleanly.
//
// Usage:
//   run_dtype <base.fvecs> <query.fvecs> [maxBase] [trainQ] [testQ] [ef]
//     -> real SIFT1M (recommended; the synthetic version flatters query-aware)
//   run_dtype                 [count] [trainQ] [testQ] [ef]
//     -> reproducible synthetic fallback (no args)

#include <algorithm>
#include <cstdint>
#include <iomanip>
#include <iostream>
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

/// Returns true if @p s looks like a path rather than a number.
bool isPath(const char* s) {
  for (const char* p = s; *p; p++) {
    if ((*p < '0' || *p > '9')) {
      return true;
    }
  }
  return false;
}

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
    uint32_t dim, uint32_t k, uint64_t first, uint64_t last) {
  TraceCollector collector(dim, sizeof(float));
  for (uint64_t q = first; q < last; q++) {
    collector.beginQuery(q);
    adapter.searchInstrumented(queries.data() + q * dim, k, collector);
  }
  return collector.trace();
}

}  // namespace

int main(int argc, char* argv[]) {
  // Parse: real mode if argv[1] is a path, else synthetic.
  const bool realMode = argc > 2 && isPath(argv[1]) && isPath(argv[2]);

  std::vector<float> base;
  std::vector<float> queries;
  uint32_t dim = 128;
  uint64_t count = 0;
  uint64_t trainQ = 0;
  uint64_t testQ = 0;
  uint32_t ef = 64;
  const uint32_t rowBytes = 2048;
  const uint32_t k = 10;

  if (realMode) {
    const std::string basePath = argv[1];
    const std::string queryPath = argv[2];
    const uint64_t maxBase = argc > 3 ? std::stoull(argv[3]) : 100000;
    trainQ = argc > 4 ? std::stoull(argv[4]) : 500;
    testQ = argc > 5 ? std::stoull(argv[5]) : 200;
    ef = argc > 6 ? std::stoul(argv[6]) : 64;

    std::cerr << "[dtype] REAL mode: loading " << basePath << " ...\n";
    const VecData b = loadFvecs(basePath, maxBase);
    const VecData q = loadFvecs(queryPath, trainQ + testQ);
    if (b.dim != q.dim) {
      std::cerr << "dim mismatch: base " << b.dim << " vs query " << q.dim
                << "\n";
      return 1;
    }
    dim = b.dim;
    count = b.count;
    base = b.data;
    queries = q.data;
    std::cerr << "[dtype] base " << count << " x " << dim << ", queries "
              << queries.size() / dim << "\n";
  } else {
    count = argc > 1 ? std::stoull(argv[1]) : 20000;
    trainQ = argc > 2 ? std::stoull(argv[2]) : 400;
    testQ = argc > 3 ? std::stoull(argv[3]) : 200;
    ef = argc > 4 ? std::stoul(argv[4]) : 64;
    std::mt19937 rng(42);
    std::cerr << "[dtype] SYNTHETIC mode (note: flatters query-aware) " << count
              << " base, dim " << dim << "\n";
    base = makeCorpus(dim, count, 64, rng);
    queries = makeCorpus(dim, trainQ + testQ, 64, rng);
  }

  HnswConfig config;
  config.dimension = dim;
  config.dtypeBytes = sizeof(float);
  config.m = 16;
  config.efSearch = ef;
  HnswAdapter adapter(config);
  std::cerr << "[dtype] building HNSW index (M=16, ef=" << ef << ")...\n";
  adapter.addVectors(base.data(), count);

  std::cerr << "[dtype] learning co-visitation on " << trainQ
            << " train queries...\n";
  const AccessTrace trainTrace =
      collectRange(adapter, queries, dim, k, 0, trainQ);
  CoVisitationModel model;
  model.accumulate(trainTrace);
  model.finalize();

  std::cerr << "[dtype] collecting " << testQ << " held-out test traces...\n";
  const AccessTrace testTrace =
      collectRange(adapter, queries, dim, k, trainQ, trainQ + testQ);

  RandomLayout randomLayout(1);
  BfsLayout bfsLayout;
  CommunityLayout communityLayout;
  QueryAwareLayout queryLayout(model, rowBytes);
  randomLayout.build(adapter);
  bfsLayout.build(adapter);
  communityLayout.build(adapter);
  queryLayout.build(adapter);

  const std::vector<std::pair<const char*, uint32_t>> dtypes = {
      {"float32", 4}, {"int8", 1}};

  std::cout << "# byte-budget sweep ("
            << (realMode ? "REAL SIFT" : "synthetic") << ", dim " << dim
            << ", ef " << ef << ")\n";
  std::cout << "dtype,vectors_per_row,layout,inter_vector_row_hit_pct,"
            << "covisit_colocation_pct\n";
  for (const auto& [name, dtypeBytes] : dtypes) {
    const uint32_t vectorBytes = dim * dtypeBytes;
    const uint32_t perRow = std::max<uint32_t>(1, rowBytes / vectorBytes);
    auto row = [&](const char* lname, const MemoryLayout& layout) {
      const LayoutMetrics m =
          computeMetrics(testTrace, layout, rowBytes, vectorBytes);
      std::cout << name << ',' << perRow << ',' << lname << ','
                << std::fixed << std::setprecision(3) << m.interVectorRowHit
                << ',' << m.covisitColocation << "\n";
    };
    row("random", randomLayout);
    row("bfs", bfsLayout);
    row("community", communityLayout);
    row("query_aware", queryLayout);
  }
  std::cerr << "[dtype] done.\n";
  return 0;
}
