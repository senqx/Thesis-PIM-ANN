// Fixed-traversal study: stock float32 HNSW, exact subset truth, held-out layouts.
#include "ann/fvecs_loader.h"
#include "ann/hnsw_adapter.h"
#include "ann/trace_collector.h"
#include "layout/bfs_layout.h"
#include "layout/community_layout.h"
#include "layout/query_aware_layout.h"
#include "layout/random_layout.h"
#include "layout_metrics.h"
#include "memory/address_emitter.h"
#include <algorithm>
#include <chrono>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <memory>
#include <numeric>
#include <random>
#include <stdexcept>
#include <unordered_set>
using namespace pimann;
namespace fs = std::filesystem;
using Clock = std::chrono::steady_clock;
static double seconds(Clock::time_point t) {
  return std::chrono::duration<double>(Clock::now() - t).count();
}
static std::ofstream output(const fs::path &p) {
  std::ofstream f(p);
  if (!f)
    throw std::runtime_error("cannot write " + p.string());
  f.exceptions(std::ios::badbit | std::ios::failbit);
  f << std::setprecision(12);
  return f;
}
class IdentityLayout final : public MemoryLayout {
  uint64_t n = 0;

public:
  std::string name() const override { return "identity"; }
  void build(const GraphView &g) override { n = g.nodeCount(); }
  uint64_t slotOf(uint64_t v) const override {
    if (v >= n)
      throw std::out_of_range("identity");
    return v;
  }
  uint64_t nodeAt(uint64_t v) const override { return slotOf(v); }
  void exportMapping(const std::string &path) const override {
    auto f = output(path);
    f << "logicalId,slot\n";
    for (uint64_t i = 0; i < n; ++i)
      f << i << ',' << i << '\n';
    f.close();
  }
};
static uint32_t number(const std::string &s) {
  size_t used;
  auto v = std::stoull(s, &used);
  if (s.empty() || s[0] == '-' || used != s.size() || v > UINT32_MAX)
    throw std::invalid_argument("invalid integer: " + s);
  return v;
}
static std::vector<uint32_t> exact(const VecData &base, const float *query, uint32_t k) {
  std::vector<std::pair<double, uint32_t>> distances;
  distances.reserve(base.count);
  for (uint32_t i = 0; i < base.count; ++i) {
    double sum = 0;
    for (uint32_t d = 0; d < base.dim; ++d) {
      double x = double(query[d]) - base.data[uint64_t(i) * base.dim + d];
      sum += x * x;
    }
    distances.emplace_back(sum, i);
  }
  std::partial_sort(distances.begin(), distances.begin() + k, distances.end());
  std::vector<uint32_t> ids;
  for (uint32_t i = 0; i < k; ++i)
    ids.push_back(distances[i].second);
  return ids;
}
int main(int argc, char **argv) try {
  std::string basepath, querypath, out = "work/synthetic";
  uint32_t n = 8000, train = 300, test = 150, ef = 64, seed = 1, indexseed = 100;
  uint32_t window = 16, block = 1024, k = 10, insertionseed = 0;
  bool traces = true;
  for (int i = 1; i < argc; ++i) {
    std::string a = argv[i];
    if (a == "--no-traces") {
      traces = false;
      continue;
    }
    if (i + 1 == argc)
      throw std::invalid_argument("missing option value");
    std::string v = argv[++i];
    if (a == "--base")
      basepath = v;
    else if (a == "--queries")
      querypath = v;
    else if (a == "--output")
      out = v;
    else if (a == "--max-base")
      n = number(v);
    else if (a == "--train")
      train = number(v);
    else if (a == "--test")
      test = number(v);
    else if (a == "--ef")
      ef = number(v);
    else if (a == "--seed")
      seed = number(v);
    else if (a == "--index-seed")
      indexseed = number(v);
    else if (a == "--insertion-seed")
      insertionseed = number(v);
    else if (a == "--window")
      window = number(v);
    else if (a == "--block-bytes")
      block = number(v);
    else if (a == "--k")
      k = number(v);
    else
      throw std::invalid_argument("unknown option: " + a);
  }
  if (!n || !train || !test || !ef || !window || !block || !k || k > n ||
      uint64_t(train) + test > UINT32_MAX)
    throw std::invalid_argument("invalid counts/parameters");
  VecData base, queries;
  if (!basepath.empty() || !querypath.empty()) {
    if (basepath.empty() || querypath.empty())
      throw std::invalid_argument("both base and query files required");
    base = loadFvecs(basepath, n);
    queries = loadFvecs(querypath);
    if (base.count != n || queries.count < uint64_t(train) + test || base.dim != queries.dim)
      throw std::invalid_argument("short dataset or inconsistent dimensions");
  } else {
    // Shared centroids; corpus/query generation is independent of split seed.
    constexpr uint32_t dim = 128, clusters = 64;
    std::mt19937 rng(7001);
    std::normal_distribution<float> center(0, 3), noise(0, 0.3);
    std::vector<float> centers(clusters * dim);
    for (auto &x : centers)
      x = center(rng);
    auto sample = [&](uint32_t count) {
      VecData data;
      data.count = count;
      data.dim = dim;
      data.data.resize(uint64_t(count) * dim);
      for (uint32_t i = 0; i < count; ++i) {
        uint32_t c = rng() % clusters;
        for (uint32_t d = 0; d < dim; ++d)
          data.data[uint64_t(i) * dim + d] = centers[c * dim + d] + noise(rng);
      }
      return data;
    };
    base = sample(n);
    queries = sample(std::max<uint32_t>(2000, train + test));
  }
  fs::create_directories(out);
  HnswConfig config;
  config.dimension = base.dim;
  config.efSearch = ef;
  config.indexSeed = indexseed;
  auto started = Clock::now();
  HnswAdapter graph(config);
  std::vector<uint32_t> insertionOrder(base.count);
  std::iota(insertionOrder.begin(), insertionOrder.end(), 0);
  if (insertionseed) {
    std::mt19937 rng(insertionseed);
    std::shuffle(insertionOrder.begin(), insertionOrder.end(), rng);
  }
  graph.addVectors(base.data.data(), base.count, insertionOrder);
  double buildsec = seconds(started);
  auto insertion = output(fs::path(out) / "insertion.csv");
  insertion << "position,corpus_id\n";
  for (uint64_t i = 0; i < insertionOrder.size(); ++i)
    insertion << i << ',' << insertionOrder[i] << '\n';
  insertion.close();
  auto topology = output(fs::path(out) / "graph.csv");
  topology << "node,level,neighbors\n";
  for (uint64_t node = 0; node < graph.nodeCount(); ++node)
    for (uint32_t level = 0; level < graph.levelCount(node); ++level) {
      topology << node << ',' << level << ',';
      for (auto neighbor : graph.neighborsAt(node, level))
        topology << neighbor << ' ';
      topology << '\n';
    }
  topology.close();
  std::cerr << "index built: " << base.count << " vectors, " << buildsec << " seconds\n";
  std::vector<uint32_t> ids(queries.count);
  std::iota(ids.begin(), ids.end(), 0);
  std::mt19937 splitrng(seed);
  std::shuffle(ids.begin(), ids.end(), splitrng);
  auto splits = output(fs::path(out) / "split.csv");
  splits << "partition,position,source_query\n";
  TraceCollector training(base.dim, 4), evaluation(base.dim, 4);
  started = Clock::now();
  for (uint32_t i = 0; i < train; ++i) {
    splits << "train," << i << ',' << ids[i] << '\n';
    training.beginQuery(i);
    graph.searchInstrumented(&queries.data[uint64_t(ids[i]) * base.dim], k, training);
  }
  double trainingsec = seconds(started);
  auto recallout = output(fs::path(out) / "recall.csv");
  recallout << "query,source_query,recall,returned,truth\n";
  double recallsum = 0;
  for (uint32_t i = 0; i < test; ++i) {
    uint32_t source = ids[queries.count - test + i];
    splits << "test," << i << ',' << source << '\n';
    const float *q = &queries.data[uint64_t(source) * base.dim];
    evaluation.beginQuery(i);
    const auto found = graph.searchInstrumented(q, k, evaluation);
    if (found != graph.searchStock(q, k))
      throw std::runtime_error("instrumentation changed search results");
    auto truth = exact(base, q, k);
    uint32_t hits = 0;
    for (auto v : found)
      hits += std::find(truth.begin(), truth.end(), v) != truth.end();
    const double recall = double(hits) / k;
    recallsum += recall;
    recallout << i << ',' << source << ',' << recall << ',';
    for (auto v : found)
      recallout << v << ' ';
    recallout << ',';
    for (auto v : truth)
      recallout << v << ' ';
    recallout << '\n';
  }
  splits.close();
  recallout.close();
  started = Clock::now();
  CoVisitationModel model(window);
  model.accumulate(training.trace());
  model.finalize();
  const double modelsec = seconds(started);
  std::unordered_set<uint64_t> trained, testnodes;
  uint64_t seen = 0, vectorreads = 0, adjreads = 0, upper = 0;
  for (auto &r : training.trace())
    if (r.kind == AccessKind::Vector)
      trained.insert(r.nodeId);
  auto logical = output(fs::path(out) / "logical.csv");
  logical << "query,node,kind,level,bytes\n";
  for (auto &r : evaluation.trace()) {
    logical << r.queryId << ',' << r.nodeId << ',' << (r.kind == AccessKind::Vector ? 'V' : 'A')
            << ',' << r.level << ',' << r.byteSpan << '\n';
    upper += r.level > 0;
    if (r.kind == AccessKind::Vector) {
      ++vectorreads;
      seen += trained.count(r.nodeId);
      testnodes.insert(r.nodeId);
    } else
      ++adjreads;
  }
  logical.close();
  auto metadata = output(fs::path(out) / "metadata.csv");
  metadata << "base_count,dimension,query_pool,train,test,k,ef,M,ef_construction,seed,index_seed,"
              "window,block_bytes,index_seconds,training_seconds,model_seconds,recall,train_nodes,"
              "test_nodes,test_access_coverage,vector_reads,adjacency_reads,upper_records,"
              "insertion_seed\n";
  metadata << n << ',' << base.dim << ',' << queries.count << ',' << train << ',' << test << ','
           << k << ',' << ef << ",16,200," << seed << ',' << indexseed << ',' << window << ','
           << block << ',' << buildsec << ',' << trainingsec << ',' << modelsec << ','
           << recallsum / test << ',' << trained.size() << ',' << testnodes.size() << ','
           << double(seen) / vectorreads << ',' << vectorreads << ',' << adjreads << ',' << upper
           << ',' << insertionseed << '\n';
  metadata.close();
  auto summary = output(fs::path(out) / "layouts.csv");
  summary << "layout,vector_bytes,block_bytes,consecutive_vector_same_block_pct,covisit_same_block_"
             "pct,reads,layout_seconds,vector_base,vector_end,adjacency_base,adjacency_end\n";
  for (uint32_t width : {base.dim * 4, base.dim}) {
    auto plan = AddressPlan::forGraph(graph, width, 32);
    std::vector<std::unique_ptr<MemoryLayout>> layouts;
    layouts.push_back(std::make_unique<IdentityLayout>());
    layouts.push_back(std::make_unique<RandomLayout>(seed));
    layouts.push_back(std::make_unique<BfsLayout>());
    layouts.push_back(std::make_unique<CommunityLayout>(20, seed));
    layouts.push_back(std::make_unique<QueryAwareLayout>(model, block, width));
    for (auto &layout : layouts) {
      started = Clock::now();
      layout->build(graph);
      double layoutsec = seconds(started);
      std::vector<bool> used(n, false);
      for (uint64_t node = 0; node < n; ++node) {
        auto s = layout->slotOf(node);
        if (s >= n || used[s] || layout->nodeAt(s) != node)
          throw std::runtime_error("invalid layout permutation");
        used[s] = true;
      }
      std::string stem = layout->name() + "_" + std::to_string(width);
      layout->exportMapping((fs::path(out) / (stem + ".mapping.csv")).string());
      auto metrics = computeMetrics(evaluation.trace(), *layout, block, width);
      uint64_t reads = 0;
      if (traces) {
        auto f = output(fs::path(out) / (stem + ".trace"));
        reads = AddressEmitter(*layout, plan).emit(evaluation.trace(), f);
        f.close();
      }
      summary << layout->name() << ',' << width << ',' << block << ','
              << metrics.consecutiveVectorSameBlockPct << ',' << metrics.covisitSameBlockPct << ','
              << reads << ',' << layoutsec << ',' << plan.vectorBase << ',' << plan.vectorEnd << ','
              << plan.adjacencyBase << ',' << plan.adjacencyEnd << '\n';
    }
  }
  summary.close();
  std::cerr << "study complete: " << out << ", Recall@" << k << '=' << recallsum / test << '\n';
  return 0;
} catch (const std::exception &e) {
  std::cerr << "run_study: " << e.what() << '\n';
  return 1;
}
