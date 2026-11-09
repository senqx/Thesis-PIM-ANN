// Full layout benchmark: train/test split, four layouts, honest metrics, and an
// efSearch sweep. Random/BFS/Community are workload-blind baselines;
// QueryAware learns from TRAINING queries only and is scored on a DISJOINT TEST
// set, so a gain reflects generalisation. The reported inter-vector row-hit is
// the honest locality metric (see layout_metrics.h); the all-burst proxy is
// shown alongside only to demonstrate how intra-vector bursts flatten it.

#include <algorithm>
#include <cstdint>
#include <iomanip>
#include <iostream>
#include <memory>
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
#include "metrics/recall_evaluator.h"

namespace {

using namespace pimann;

struct Corpus {
  std::vector<float> base;
  std::vector<float> query;
  uint32_t dim;
  uint64_t count;
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
  Corpus corpus{{}, {}, dim, count};
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
  std::partial_sort(dist.begin(), dist.begin() + k, dist.end());
  std::vector<uint32_t> out;
  for (uint32_t i = 0; i < k; i++) {
    out.push_back(dist[i].second);
  }
  return out;
}

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
      p_recall->addQuery(exactTopK(corpus, p_query, k), got);
    }
  }
  return collector.trace();
}

void reportRow(
    const std::string& name, const LayoutMetrics& m, double recall) {
  std::cout << std::left << std::setw(13) << name << std::right
            << std::fixed << std::setprecision(3)
            << std::setw(12) << m.allBurstRowHit
            << std::setw(14) << m.interVectorRowHit
            << std::setw(14) << m.covisitColocation
            << std::setw(10) << recall << "\n";
}

}  // namespace

int main(int argc, char* argv[]) {
  const uint64_t count = argc > 1 ? std::stoull(argv[1]) : 20000;
  const uint64_t trainQ = argc > 2 ? std::stoull(argv[2]) : 400;
  const uint64_t testQ = argc > 3 ? std::stoull(argv[3]) : 200;
  const uint32_t dim = 128;
  const uint32_t rowBytes = 2048;
  const uint32_t k = 10;

  // efSearch sweep: wider ef visits more nodes per query, so more co-visited
  // pairs can fit a row -- the sweep shows the layout ordering is stable, not
  // an artefact of one ef.
  const std::vector<uint32_t> efSweep = {32, 64, 128, 256};
  const uint32_t vectorBytes = dim * sizeof(float);

  std::cerr << "[bench] corpus " << count << " base, " << trainQ
            << " train + " << testQ << " test, dim " << dim << "\n";
  const Corpus corpus = makeSynthetic(dim, count, trainQ + testQ, 64);

  for (const uint32_t ef : efSweep) {
    HnswConfig config;
    config.dimension = dim;
    config.dtypeBytes = sizeof(float);
    config.m = 16;
    config.efSearch = ef;

    HnswAdapter adapter(config);
    adapter.addVectors(corpus.base.data(), count);

    // Train co-visitation on TRAIN queries; evaluate on held-out TEST.
    const AccessTrace trainTrace = collectRange(
        adapter, corpus, dim, config.dtypeBytes, k, 0, trainQ, nullptr);
    CoVisitationModel model;
    model.accumulate(trainTrace);
    model.finalize();

    RecallEvaluator recall(k);
    const AccessTrace testTrace = collectRange(
        adapter, corpus, dim, config.dtypeBytes, k, trainQ, trainQ + testQ,
        &recall);

    RandomLayout randomLayout(1);
    BfsLayout bfsLayout;
    CommunityLayout communityLayout;
    QueryAwareLayout queryLayout(model, rowBytes);
    randomLayout.build(adapter);
    bfsLayout.build(adapter);
    communityLayout.build(adapter);
    queryLayout.build(adapter);

    std::cout << "\n=== efSearch=" << ef << "  (Recall@" << k << "="
              << std::fixed << std::setprecision(3) << recall.recall()
              << ") ===\n";
    std::cout << std::left << std::setw(13) << "layout" << std::right
              << std::setw(12) << "allBurst%" << std::setw(14) << "interVec%"
              << std::setw(14) << "coloc%" << std::setw(10) << "recall"
              << "\n";
    reportRow(
        "random", computeMetrics(testTrace, randomLayout, rowBytes, vectorBytes),
        recall.recall());
    reportRow(
        "bfs", computeMetrics(testTrace, bfsLayout, rowBytes, vectorBytes),
        recall.recall());
    reportRow(
        "community",
        computeMetrics(testTrace, communityLayout, rowBytes, vectorBytes),
        recall.recall());
    reportRow(
        "query_aware",
        computeMetrics(testTrace, queryLayout, rowBytes, vectorBytes),
        recall.recall());
  }
  return 0;
}
