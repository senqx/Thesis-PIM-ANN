// Proposed-layout evaluation with a train/test split.
//
// Protocol (the scientifically important part): learn the co-visitation model
// from a TRAINING query set, build every layout, then score DRAM locality on a
// DISJOINT TEST query set. A gain on held-out queries reflects generalisation,
// not memorising the scored workload. Random and BFS ignore the training set
// and serve as workload-blind baselines.
//
// Ramulator is not built here, so locality is reported with a row-hit proxy
// (configurable row size); the emitted .ldst files feed the real simulator for
// cycle-accurate numbers.

#include <algorithm>
#include <cstdint>
#include <fstream>
#include <iostream>
#include <random>
#include <sstream>
#include <string>
#include <vector>

#include "ann/hnsw_adapter.h"
#include "ann/trace_collector.h"
#include "layout/bfs_layout.h"
#include "layout/covisitation_model.h"
#include "layout/query_aware_layout.h"
#include "layout/random_layout.h"
#include "memory/address_emitter.h"
#include "metrics/recall_evaluator.h"

namespace {

using namespace pimann;

struct Corpus {
  std::vector<float> base;
  std::vector<float> query;
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

/// Run queries [first, last) through instrumented search into a fresh trace.
AccessTrace collectRange(
    const HnswAdapter& adapter, const Corpus& corpus, uint32_t dim,
    uint32_t dtypeBytes, uint32_t k, uint64_t first, uint64_t last,
    RecallEvaluator* p_recall) {
  TraceCollector collector(dim, dtypeBytes);
  for (uint64_t q = first; q < last; q++) {
    collector.beginQuery(q);
    const float* p_query = corpus.query.data() + q * dim;
    const std::vector<uint32_t> got =
        adapter.searchInstrumented(p_query, k, collector);
    if (p_recall != nullptr) {
      // brute-force ground truth
      std::vector<std::pair<float, uint32_t>> dist(corpus.count);
      for (uint64_t i = 0; i < corpus.count; i++) {
        float sum = 0.0f;
        for (uint32_t d = 0; d < dim; d++) {
          const float diff = corpus.base[i * dim + d] - p_query[d];
          sum += diff * diff;
        }
        dist[i] = {sum, static_cast<uint32_t>(i)};
      }
      std::partial_sort(dist.begin(), dist.begin() + k, dist.end());
      std::vector<uint32_t> truth;
      for (uint32_t i = 0; i < k; i++) {
        truth.push_back(dist[i].second);
      }
      p_recall->addQuery(truth, got);
    }
  }
  return collector.trace();
}

/// Co-location quality: of all distinct node pairs co-visited within the same
/// held-out test query, what fraction land in the same DRAM row under a layout
/// (same block of blockSize consecutive slots)? This measures exactly what a
/// query-aware layout targets, free of the burst/adjacency noise in the row-hit
/// proxy. Sampled per query to stay cheap on large traces.
double colocation(
    const AccessTrace& trace, const MemoryLayout& layout, uint32_t blockSize) {
  uint64_t sameRow = 0;
  uint64_t pairs = 0;
  uint64_t currentQuery = 0;
  bool haveQuery = false;
  std::vector<uint32_t> nodes;

  auto flush = [&]() {
    std::sort(nodes.begin(), nodes.end());
    nodes.erase(std::unique(nodes.begin(), nodes.end()), nodes.end());
    for (size_t i = 0; i < nodes.size(); i++) {
      for (size_t j = i + 1; j < nodes.size(); j++) {
        const uint64_t ri = layout.slotOf(nodes[i]) / blockSize;
        const uint64_t rj = layout.slotOf(nodes[j]) / blockSize;
        if (ri == rj) {
          sameRow++;
        }
        pairs++;
      }
    }
    nodes.clear();
  };

  for (const AccessRecord& record : trace) {
    if (record.kind != AccessKind::Vector) {
      continue;
    }
    if (!haveQuery || record.queryId != currentQuery) {
      flush();
      currentQuery = record.queryId;
      haveQuery = true;
    }
    nodes.push_back(static_cast<uint32_t>(record.nodeId));
  }
  flush();
  return pairs > 0 ? 100.0 * sameRow / pairs : 0.0;
}

/// Row-hit proxy: fraction of burst reads landing in the same DRAM row as the
/// previous read. Directional stand-in for Ramulator's row-hit rate.
double rowHitProxy(
    const AccessTrace& trace, MemoryLayout& r_layout, uint32_t rowBytes) {
  AddressPlan plan;
  AddressEmitter emitter(r_layout, plan);
  std::ostringstream oss;
  emitter.emit(trace, oss);
  const std::string text = oss.str();

  uint64_t hits = 0;
  uint64_t total = 0;
  uint64_t prevRow = ~0ull;
  std::istringstream in(text);
  std::string tok, addr;
  while (in >> tok >> addr) {
    const uint64_t a = std::stoull(addr, nullptr, 16);
    const uint64_t row = a / rowBytes;
    if (total > 0 && row == prevRow) {
      hits++;
    }
    prevRow = row;
    total++;
  }
  return total > 1 ? 100.0 * hits / (total - 1) : 0.0;
}

}  // namespace

int main(int argc, char* argv[]) {
  HnswConfig config;
  config.dimension = 128;
  config.dtypeBytes = sizeof(float);
  config.m = 16;
  config.efSearch = 64;

  const uint64_t count = argc > 1 ? std::stoull(argv[1]) : 20000;
  const uint64_t trainQ = argc > 2 ? std::stoull(argv[2]) : 400;
  const uint64_t testQ = argc > 3 ? std::stoull(argv[3]) : 200;
  const uint32_t rowBytes = 2048;
  const uint32_t k = 10;

  std::cerr << "[proposed] corpus " << count << " base, " << trainQ
            << " train + " << testQ << " test queries, dim "
            << config.dimension << "\n";
  const Corpus corpus =
      makeSynthetic(config.dimension, count, trainQ + testQ, /*clusters=*/64);

  HnswAdapter adapter(config);
  std::cerr << "[proposed] building HNSW index...\n";
  adapter.addVectors(corpus.base.data(), count);

  // Learn co-visitation from TRAINING queries only.
  std::cerr << "[proposed] collecting TRAIN traces...\n";
  const AccessTrace trainTrace = collectRange(
      adapter, corpus, config.dimension, config.dtypeBytes, k, 0, trainQ,
      nullptr);
  CoVisitationModel model;
  model.accumulate(trainTrace);
  model.finalize();

  // Evaluate on DISJOINT TEST queries; track recall (layout-independent).
  std::cerr << "[proposed] collecting held-out TEST traces...\n";
  RecallEvaluator recall(k);
  const AccessTrace testTrace = collectRange(
      adapter, corpus, config.dimension, config.dtypeBytes, k, trainQ,
      trainQ + testQ, &recall);

  // Build all three layouts (random/bfs are workload-blind; query-aware uses
  // the training model).
  RandomLayout randomLayout(1);
  BfsLayout bfsLayout;
  QueryAwareLayout queryLayout(model, rowBytes);
  randomLayout.build(adapter);
  bfsLayout.build(adapter);
  queryLayout.build(adapter);

  // Score locality on the held-out test trace.
  const double rRandom = rowHitProxy(testTrace, randomLayout, rowBytes);
  const double rBfs = rowHitProxy(testTrace, bfsLayout, rowBytes);
  const double rQuery = rowHitProxy(testTrace, queryLayout, rowBytes);

  // Direct co-location quality on held-out co-visited pairs (block = vectors
  // per DRAM row).
  const uint32_t vectorBytes = config.dimension * config.dtypeBytes;
  const uint32_t blockSize = std::max<uint32_t>(1, rowBytes / vectorBytes);
  const double cRandom = colocation(testTrace, randomLayout, blockSize);
  const double cBfs = colocation(testTrace, bfsLayout, blockSize);
  const double cQuery = colocation(testTrace, queryLayout, blockSize);

  std::cerr << "[proposed] Recall@" << k << " (test): " << recall.recall()
            << "   block=" << blockSize << " vectors/row\n";
  std::cout << "layout,row_hit_proxy_pct,covisit_colocation_pct,recall@" << k
            << "\n";
  std::cout << "random," << rRandom << ',' << cRandom << ','
            << recall.recall() << "\n";
  std::cout << "bfs," << rBfs << ',' << cBfs << ',' << recall.recall() << "\n";
  std::cout << "query_aware," << rQuery << ',' << cQuery << ','
            << recall.recall() << "\n";

  // Emit the held-out test trace under each layout for Ramulator.
  {
    AddressPlan plan;
    std::ofstream o1("test_random.ldst");
    AddressEmitter(randomLayout, plan).emit(testTrace, o1);
    std::ofstream o2("test_bfs.ldst");
    AddressEmitter(bfsLayout, plan).emit(testTrace, o2);
    std::ofstream o3("test_query_aware.ldst");
    AddressEmitter(queryLayout, plan).emit(testTrace, o3);
  }
  std::cerr << "[proposed] wrote test_{random,bfs,query_aware}.ldst\n";
  return 0;
}