#include "ann/hnsw_adapter.h"

#include <queue>
#include <unordered_set>
#include <utility>
#include <vector>

#include "ann/trace_collector.h"
#include "hnswlib/hnswlib.h"

namespace pimann {

/// Owns the hnswlib index and its L2 space. Hidden behind a pimpl so hnswlib's
/// headers never leak into our other translation units.
struct HnswAdapter::Impl {
  explicit Impl(const HnswConfig& config)
      : space(config.dimension) {}

  hnswlib::L2Space space;
  std::unique_ptr<hnswlib::HierarchicalNSW<float>> index;
  // Cached base-layer adjacency, materialised once for the GraphView so layout
  // strategies get cheap const-ref access without re-reading index memory.
  std::vector<std::vector<uint32_t>> adjacency;
};

HnswAdapter::HnswAdapter(HnswConfig config)
    : m_config(config), m_impl(std::make_unique<Impl>(config)) {}

HnswAdapter::~HnswAdapter() = default;

void HnswAdapter::addVectors(const float* p_data, uint64_t count) {
  m_impl->index = std::make_unique<hnswlib::HierarchicalNSW<float>>(
      &m_impl->space, count, m_config.m, m_config.efConstruction);
  for (uint64_t i = 0; i < count; i++) {
    m_impl->index->addPoint(p_data + i * m_config.dimension, i);
  }
  m_impl->index->setEf(m_config.efSearch);

  // Snapshot base-layer neighbour lists for the GraphView.
  m_impl->adjacency.assign(count, {});
  for (uint64_t node = 0; node < count; node++) {
    const auto* p_list = reinterpret_cast<const uint32_t*>(
        m_impl->index->get_linklist0(static_cast<unsigned>(node)));
    const unsigned degree = m_impl->index->getListCount(
        const_cast<unsigned*>(p_list));
    auto& r_edges = m_impl->adjacency[node];
    r_edges.reserve(degree);
    for (unsigned j = 1; j <= degree; j++) {
      r_edges.push_back(p_list[j]);
    }
  }
}

std::vector<uint32_t> HnswAdapter::searchInstrumented(
    const float* p_query, uint32_t k, TraceCollector& r_collector) const {
  // Faithful reimplementation of hnswlib's base-layer greedy search
  // (searchBaseLayerST), instrumented to record exactly the two memory reads
  // the real loop performs per expansion: the node's neighbour list
  // (Adjacency) and each candidate's vector (Vector). Upper layers are not
  // traced; they are a negligible fraction of traffic. Results match
  // hnswlib because the traversal and distance order are identical.
  auto& r_index = *m_impl->index;
  const auto p_dist = r_index.fstdistfunc_;
  void* p_param = r_index.dist_func_param_;

  // Greedy descent through the upper layers to find a good base-layer entry
  // point (not traced; cheap, few nodes).
  hnswlib::tableint entry = r_index.enterpoint_node_;
  float entryDist = p_dist(
      p_query, r_index.getDataByInternalId(entry), p_param);
  for (int level = r_index.maxlevel_; level > 0; level--) {
    bool changed = true;
    while (changed) {
      changed = false;
      const auto* p_list = r_index.get_linklist(entry, level);
      const unsigned degree = r_index.getListCount(
          const_cast<unsigned*>(p_list));
      for (unsigned j = 1; j <= degree; j++) {
        const hnswlib::tableint cand = p_list[j];
        const float d = p_dist(
            p_query, r_index.getDataByInternalId(cand), p_param);
        if (d < entryDist) {
          entryDist = d;
          entry = cand;
          changed = true;
        }
      }
    }
  }

  // Base-layer best-first search. top = far-first max-heap of results (size ef),
  // candidates = near-first min-heap of the frontier.
  using Pair = std::pair<float, hnswlib::tableint>;
  std::priority_queue<Pair> top;  // max-heap by distance
  std::priority_queue<Pair, std::vector<Pair>, std::greater<Pair>> candidates;
  std::unordered_set<hnswlib::tableint> visited;

  candidates.emplace(entryDist, entry);
  top.emplace(entryDist, entry);
  visited.insert(entry);
  float worst = entryDist;
  const size_t ef = r_index.ef_;

  while (!candidates.empty()) {
    const Pair current = candidates.top();
    if (current.first > worst && top.size() >= ef) {
      break;
    }
    candidates.pop();
    const hnswlib::tableint node = current.second;

    // Read this node's neighbour list to expand it.
    r_collector.onAccess(
        node, AccessKind::Adjacency, 0,
        /*byteSpan=*/m_impl->adjacency[node].size() * sizeof(uint32_t)
            + sizeof(uint32_t));

    for (const uint32_t neighbor : m_impl->adjacency[node]) {
      if (visited.count(neighbor) != 0) {
        continue;
      }
      visited.insert(neighbor);

      // Read the neighbour's vector to compute its distance.
      r_collector.onAccess(neighbor, AccessKind::Vector, 0);
      const float d = p_dist(
          p_query, r_index.getDataByInternalId(neighbor), p_param);

      if (top.size() < ef || d < worst) {
        candidates.emplace(d, neighbor);
        top.emplace(d, neighbor);
        if (top.size() > ef) {
          top.pop();
        }
        worst = top.top().first;
      }
    }
  }

  // Drain the result heap; it is far-first, so reverse into best-first order and
  // keep the top k external labels.
  std::vector<uint32_t> result;
  result.reserve(top.size());
  while (!top.empty()) {
    result.push_back(
        static_cast<uint32_t>(r_index.getExternalLabel(top.top().second)));
    top.pop();
  }
  std::reverse(result.begin(), result.end());
  if (result.size() > k) {
    result.resize(k);
  }
  return result;
}

uint64_t HnswAdapter::nodeCount() const {
  return m_impl->adjacency.size();
}

const std::vector<uint32_t>& HnswAdapter::neighbors(uint64_t nodeId) const {
  return m_impl->adjacency[nodeId];
}

}  // namespace pimann
