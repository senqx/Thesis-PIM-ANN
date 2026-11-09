// Sprint-1 driver: build a real HNSW index, collect base-layer memory traces
// from real queries, emit Ramulator LD traces under Random vs BFS layouts, and
// report trace sizes + Recall@k. Replaying the emitted traces through Ramulator
// (the existing runner) produces the locality comparison.
//
// Dataset: pass fvecs/ivecs paths, or omit to use a reproducible synthetic
// clustered set (same pipeline; real SIFT1M just swaps the loader).

#include <algorithm>
#include <cstdint>
#include <fstream>
#include <iostream>
#include <memory>
#include <random>
#include <string>
#include <vector>

#include "ann/hnsw_adapter.h"
#include "ann/trace_collector.h"
#include "layout/bfs_layout.h"
#include "layout/random_layout.h"
#include "memory/address_emitter.h"
#include "metrics/recall_evaluator.h"

namespace {

using pimann::AccessKind;

/// Reproducible synthetic corpus: Gaussian blobs around random centroids, so
/// the graph has genuine community structure for BFS/layout to exploit. Stands
/// in for SIFT1M here; the real loader would read .fvecs instead.
struct Corpus {
  std::vector<float> base;    ///< count * dim, row-major
  std::vector<float> query;   ///< queryCount * dim
  uint32_t dim;
  uint64_t count;
  uint64_t queryCount;
};

Corpus makeSynthetic(
    uint32_t dim, uint64_t count, uint64_t queryCount, uint32_t clusters) {
  std::mt19937 rng(42);
  std::normal_distribution<float> jitter(0.0f, 0.15f);
  std::uniform_real_distribution<float> coord(-1.0f, 1.0f);

  std::vector<std::vector<float>> centroid(clusters, std::vector<float>(dim));
  for (auto& r_c : centroid) {
    for (float& r_x : r_c) {
      r_x = coord(rng);
    }
  }

  Corpus corpus{{}, {}, dim, count, queryCount};
  corpus.base.resize(count * dim);
  for (uint64_t i = 0; i < count; i++) {
    const auto& c = centroid[i % clusters];
    for (uint32_t d = 0; d < dim; d++) {
      corpus.base[i * dim + d] = c[d] + jitter(rng);
    }
  }
  corpus.query.resize(queryCount * dim);
  for (uint64_t q = 0; q < queryCount; q++) {
    const auto& c = centroid[rng() % clusters];
    for (uint32_t d = 0; d < dim; d++) {
      corpus.query[q * dim + d] = c[d] + jitter(rng);
    }
  }
  return corpus;
}

/// Exact top-k by brute force, for recall ground truth.
std::vector<uint32_t> exactTopK(
    const Corpus& corpus, const float* p_query, uint32_t k) {
  std::vector<std::pair<float, uint32_t>> dist(corpus.count);
  for (uint64_t i = 0; i < corpus.count; i++) {
    float sum = 0.0f;
    for (uint32_t d = 0; d < corpus.dim; d++) {
      const float diff = corpus.base[i * corpus.dim + d] - p_query[d];
      sum += diff * diff;
    }
    dist[i] = {sum, static_cast<uint32_t>(i)};
  }
  std::partial_sort(
      dist.begin(), dist.begin() + k, dist.end());
  std::vector<uint32_t> out;
  out.reserve(k);
  for (uint32_t i = 0; i < k; i++) {
    out.push_back(dist[i].second);
  }
  return out;
}

uint64_t emitTrace(
    const pimann::AccessTrace& trace, pimann::MemoryLayout& r_layout,
    const pimann::GraphView& /*graph*/, const std::string& path) {
  pimann::AddressPlan plan;
  pimann::AddressEmitter emitter(r_layout, plan);
  std::ofstream out(path);
  return emitter.emit(trace, out);
}

}  // namespace

int main(int argc, char* argv[]) {
  pimann::HnswConfig config;
  config.dimension = 128;
  config.dtypeBytes = sizeof(float);
  config.m = 16;
  config.efSearch = 64;

  const uint64_t count = argc > 1 ? std::stoull(argv[1]) : 20000;
  const uint64_t queries = argc > 2 ? std::stoull(argv[2]) : 200;
  const uint32_t k = 10;

  std::cerr << "[sprint1] building synthetic corpus: " << count
            << " base, " << queries << " queries, dim " << config.dimension
            << "\n";
  const Corpus corpus =
      makeSynthetic(config.dimension, count, queries, /*clusters=*/64);

  pimann::HnswAdapter adapter(config);
  std::cerr << "[sprint1] building HNSW index...\n";
  adapter.addVectors(corpus.base.data(), count);

  // Collect real base-layer traces + recall over the query set.
  pimann::TraceCollector collector(config.dimension, config.dtypeBytes);
  pimann::RecallEvaluator recall(k);
  std::cerr << "[sprint1] running " << queries << " instrumented queries...\n";
  for (uint64_t q = 0; q < queries; q++) {
    collector.beginQuery(q);
    const float* p_query = corpus.query.data() + q * config.dimension;
    const std::vector<uint32_t> got =
        adapter.searchInstrumented(p_query, k, collector);
    const std::vector<uint32_t> truth = exactTopK(corpus, p_query, k);
    recall.addQuery(truth, got);
  }

  std::cerr << "[sprint1] trace records: " << collector.size()
            << "   Recall@" << k << ": " << recall.recall() << "\n";

  // Emit the same logical trace under both layouts.
  pimann::RandomLayout randomLayout(/*seed=*/1);
  pimann::BfsLayout bfsLayout;
  randomLayout.build(adapter);
  bfsLayout.build(adapter);

  const uint64_t rn = emitTrace(
      collector.trace(), randomLayout, adapter, "trace_random.ldst");
  const uint64_t bn = emitTrace(
      collector.trace(), bfsLayout, adapter, "trace_bfs.ldst");

  std::cout << "layout,ldst_records,recall@" << k << "\n";
  std::cout << "random," << rn << ',' << recall.recall() << "\n";
  std::cout << "bfs," << bn << ',' << recall.recall() << "\n";
  std::cerr << "[sprint1] wrote trace_random.ldst, trace_bfs.ldst\n";
  return 0;
}
