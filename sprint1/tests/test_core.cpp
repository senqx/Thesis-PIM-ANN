#include "ann/fvecs_loader.h"
#include "ann/hnsw_adapter.h"
#include "ann/trace_collector.h"
#include "hnswlib/hnswlib.h"
#include "layout/bfs_layout.h"
#include "layout/query_aware_layout.h"
#include "layout_metrics.h"
#include "memory/address_emitter.h"
#include "metrics/recall_evaluator.h"
#include <algorithm>
#include <cassert>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <numeric>
#include <random>
#include <sstream>
#include <stdexcept>
using namespace pimann;
struct Graph : GraphView {
  std::vector<std::vector<uint32_t>> lists;
  explicit Graph(size_t n) : lists(n) {}
  uint64_t nodeCount() const override { return lists.size(); }
  uint32_t dimension() const override { return 128; }
  uint32_t dtypeBytes() const override { return 4; }
  const std::vector<uint32_t> &neighbors(uint64_t n) const override { return lists.at(n); }
};
template <class F> void rejects(F f) {
  bool threw = false;
  try {
    f();
  } catch (const std::exception &) {
    threw = true;
  }
  assert(threw);
}
int main() {
  RecallEvaluator recall(2);
  recall.addQuery({1, 2}, {2, 3});
  assert(recall.recall() == 0.5);
  rejects([&] { recall.addQuery({1, 2}, {1, 1}); });
  rejects([&] { recall.addQuery({1}, {1}); });
  Graph g(40);
  for (auto &list : g.lists)
    for (uint32_t n = 0; n < 32; ++n)
      list.push_back(n);
  BfsLayout layout;
  layout.build(g);
  auto p = AddressPlan::forGraph(g, 512);
  assert(p.adjacencyOffsets[1][0] - p.adjacencyOffsets[0][0] == 160);
  assert(p.vectorEnd < p.adjacencyBase);
  for (size_t n = 1; n < 40; ++n)
    assert(p.adjacencyOffsets[n - 1][0] + p.adjacencySpans[n - 1][0] <= p.adjacencyOffsets[n][0]);
  AccessTrace t{{0, 0, AccessKind::Adjacency, 0, 132}, {0, 1, AccessKind::Adjacency, 0, 132}};
  std::ostringstream out;
  assert(AddressEmitter(layout, p).emit(t, out) == 10);
  auto partial = AddressPlan::forGraph(g, 65);
  std::ostringstream tail;
  assert(AddressEmitter(layout, partial).emit({{0, 1, AccessKind::Vector, 0, 512}}, tail) == 3);
  rejects([&] { AddressEmitter(layout, p).addressOf({0, 0, AccessKind::Adjacency, 0, 64}); });
  rejects([&] { AddressPlan::forGraph(g, 512, 63); });
  auto m = computeMetrics({{0, 0, AccessKind::Vector, 0, 512}, {1, 1, AccessKind::Vector, 0, 512}},
                          layout, 2048, 512);
  assert(m.transitions == 0 && m.consecutiveVectorSameBlockPct == 0);
  m = computeMetrics({{0, 0, AccessKind::Vector, 0, 512}, {0, 1, AccessKind::Vector, 0, 512}},
                     layout, 2048, 512);
  assert(m.transitions == 1 && m.consecutiveVectorSameBlockPct == 100);
  // Three-node first group leaves one slot; the next seed's partners must wait.
  Graph small(7);
  CoVisitationModel model(16);
  AccessTrace train;
  for (int repeat = 0; repeat < 5; ++repeat)
    for (int n : {0, 1, 2})
      train.push_back({uint64_t(repeat), uint64_t(n), AccessKind::Vector, 0, 512});
  for (int n : {3, 4, 5, 6})
    train.push_back({5, uint64_t(n), AccessKind::Vector, 0, 512});
  model.accumulate(train);
  model.finalize();
  QueryAwareLayout wide(model, 2048, 512), narrow(model, 2048, 128);
  wide.build(small);
  narrow.build(small);
  assert(wide.slotOf(3) == 3);
  assert(wide.slotOf(4) / 4 != wide.slotOf(3) / 4);
  for (uint64_t n = 0; n < 7; ++n) {
    assert(wide.nodeAt(wide.slotOf(n)) == n);
    assert(narrow.nodeAt(narrow.slotOf(n)) == n);
  }
  // Same seed has different partner capacity at the two footprints.
  Graph larger(20);
  CoVisitationModel dense;
  AccessTrace all;
  for (uint64_t n : {1, 4, 8, 12, 16, 19})
    for (uint64_t r = 0; r < 20 - n; ++r) {
      all.push_back({n * 100 + r, 0, AccessKind::Vector, 0, 512});
      all.push_back({n * 100 + r, n, AccessKind::Vector, 0, 512});
    }
  for (uint64_t n : {3, 5, 6})
    for (uint64_t r = 0; r < 20; ++r) {
      all.push_back({3000 + n * 100 + r, 2, AccessKind::Vector, 0, 512});
      all.push_back({3000 + n * 100 + r, n, AccessKind::Vector, 0, 512});
    }
  dense.accumulate(all);
  dense.finalize();
  QueryAwareLayout w(dense, 2048, 512), b(dense, 2048, 128);
  w.build(larger);
  b.build(larger);
  bool differs = false;
  for (uint64_t n = 0; n < 20; ++n)
    differs |= w.slotOf(n) != b.slotOf(n);
  assert(differs);
  // Tie-heavy and continuous data, including ef < k. Independent stock index.
  for (bool shuffled : {false, true})
    for (bool ties : {false, true}) {
      constexpr uint32_t n = 300, dim = 8;
      std::mt19937 rng(5);
      std::vector<float> data(n * dim);
      for (auto &x : data)
        x = ties ? float(rng() % 4) : float(rng() % 100000) / 10000;
      HnswConfig cfg;
      cfg.dimension = dim;
      cfg.m = 8;
      std::vector<uint32_t> order(n);
      std::iota(order.begin(), order.end(), 0);
      if (shuffled)
        std::shuffle(order.begin(), order.end(), rng);
      HnswAdapter adapter(cfg);
      adapter.addVectors(data.data(), n, order);
      hnswlib::L2Space space(dim);
      hnswlib::HierarchicalNSW<float> reference(&space, n, 8, 200, 100);
      for (auto i : order)
        reference.addPoint(data.data() + i * dim, i);
      for (uint32_t internal = 0; internal < n; ++internal) {
        const auto corpus = order[internal];
        assert(adapter.levelCount(corpus) == uint32_t(reference.element_levels_[internal] + 1));
        for (uint32_t level = 0; level < adapter.levelCount(corpus); ++level) {
          auto *list = reference.get_linklist_at_level(internal, level);
          const auto &neighbors = adapter.neighborsAt(corpus, level);
          assert(neighbors.size() == reference.getListCount(list));
          for (size_t i = 0; i < neighbors.size(); ++i)
            assert(neighbors[i] == reference.getExternalLabel(list[i + 1]));
        }
      }
      for (uint32_t ef : {4, 64}) {
        adapter.setEf(ef);
        reference.setEf(ef);
        for (uint32_t qi = 0; qi < 100; ++qi) {
          std::vector<float> q(dim);
          for (auto &x : q)
            x = ties ? float(rng() % 4) : float(rng() % 100000) / 10000;
          TraceCollector collector(dim, 4);
          auto observed = adapter.searchInstrumented(q.data(), 10, collector);
          auto heap = reference.searchKnn(q.data(), 10);
          std::vector<uint32_t> expected;
          while (!heap.empty()) {
            expected.push_back(heap.top().second);
            heap.pop();
          }
          std::reverse(expected.begin(), expected.end());
          assert(observed == expected && observed.size() == 10);
          assert(!collector.trace().empty());
          assert(collector.trace().front().kind == AccessKind::Vector);
          for (auto &r : collector.trace())
            assert(r.nodeId < n);
          for (auto &r : collector.trace())
            if (r.kind == AccessKind::Adjacency)
              assert(r.byteSpan == 4 + 4 * adapter.neighborsAt(r.nodeId, r.level).size());
        }
      }
      rejects([&] { adapter.searchStock(data.data(), 0); });
      rejects([&] { adapter.addVectors(data.data(), n, {0, 1}); });
      auto invalid = order;
      invalid[0] = invalid[1];
      rejects([&] { adapter.addVectors(data.data(), n, invalid); });
    }
  // Corrupt records fail rather than appearing to be clean EOF.
  auto file = std::filesystem::temp_directory_path() / "pimann-loader-test.fvecs";
  {
    std::ofstream f(file, std::ios::binary);
    f.put(1);
  }
  rejects([&] { loadFvecs(file.string()); });
  {
    std::ofstream f(file, std::ios::binary);
    int dim = 2;
    f.write(reinterpret_cast<char *>(&dim), 4);
    float x = 1;
    f.write(reinterpret_cast<char *>(&x), 4);
  }
  rejects([&] { loadFvecs(file.string()); });
  std::filesystem::remove(file);
  std::cout
      << "Core invariants and 800 stock-search comparisons (corpus/shuffled insertion) passed\n";
}
