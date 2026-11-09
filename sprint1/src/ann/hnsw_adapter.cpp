#include "ann/hnsw_adapter.h"
#include "ann/trace_collector.h"
#include "hnswlib/hnswlib.h"
#include <algorithm>
#include <cmath>
#include <limits>
#include <numeric>
#include <stdexcept>
namespace pimann {
struct HnswAdapter::Impl {
  explicit Impl(const HnswConfig &c) : space(c.dimension) {}
  hnswlib::L2Space space;
  std::unique_ptr<hnswlib::HierarchicalNSW<float>> index;
  std::vector<std::vector<std::vector<uint32_t>>> adjacency;
  std::vector<uint32_t> corpusIds;
};
HnswAdapter::HnswAdapter(HnswConfig c) : m_config(c) {
  if (!c.dimension || c.dimension > 65536 || c.dtypeBytes != 4 || c.m < 2 || !c.efConstruction ||
      !c.efSearch)
    throw std::invalid_argument(
        "HNSW needs positive dimensions/ef, M >= 2 and float32 computation");
  m_impl = std::make_unique<Impl>(c);
}
HnswAdapter::~HnswAdapter() = default;
void HnswAdapter::addVectors(const float *data, uint64_t count,
                             const std::vector<uint32_t> &insertionOrder) {
  if (!data || !count || count > std::numeric_limits<uint32_t>::max())
    throw std::invalid_argument("invalid vector count");
  for (uint64_t i = 0; i < count * m_config.dimension; ++i)
    if (!std::isfinite(data[i]))
      throw std::invalid_argument("nonfinite base component");
  std::vector<uint32_t> order = insertionOrder;
  if (order.empty()) {
    order.resize(count);
    std::iota(order.begin(), order.end(), 0);
  }
  if (order.size() != count)
    throw std::invalid_argument("insertion order must contain every corpus ID");
  std::vector<bool> seen(count, false);
  for (auto id : order) {
    if (id >= count || seen[id])
      throw std::invalid_argument("insertion order must be a permutation");
    seen[id] = true;
  }
  m_impl->corpusIds = order;
  m_impl->index = std::make_unique<hnswlib::HierarchicalNSW<float>>(
      &m_impl->space, count, m_config.m, m_config.efConstruction, m_config.indexSeed);
  for (auto i : order)
    m_impl->index->addPoint(data + i * m_config.dimension, i);
  m_impl->index->setEf(m_config.efSearch);
  m_impl->adjacency.resize(count);
  for (uint64_t internal = 0; internal < count; ++internal) {
    auto &levels = m_impl->adjacency[order[internal]];
    levels.resize(m_impl->index->element_levels_[internal] + 1);
    for (uint32_t l = 0; l < levels.size(); ++l) {
      auto *list = m_impl->index->get_linklist_at_level(internal, l);
      const auto degree = m_impl->index->getListCount(list);
      levels[l].assign(list + 1, list + 1 + degree);
      for (auto &neighbor : levels[l])
        neighbor = order.at(neighbor);
    }
  }
}
std::vector<uint32_t> HnswAdapter::searchStock(const float *query, uint32_t k) const {
  if (!m_impl->index || !query || !k || k > nodeCount())
    throw std::invalid_argument("invalid query or k");
  for (uint32_t d = 0; d < m_config.dimension; ++d)
    if (!std::isfinite(query[d]))
      throw std::invalid_argument("nonfinite query component");
  auto heap = m_impl->index->searchKnn(query, k);
  std::vector<uint32_t> ids;
  while (!heap.empty()) {
    ids.push_back(heap.top().second);
    heap.pop();
  }
  std::reverse(ids.begin(), ids.end());
  return ids;
}
std::vector<uint32_t> HnswAdapter::searchInstrumented(const float *query, uint32_t k,
                                                      TraceCollector &collector) const {
  if (!m_impl->index)
    throw std::logic_error("index not built");
  auto &observer = m_impl->index->access_observer;
  observer = [&](uint32_t node, bool adjacency, unsigned level, size_t bytes) {
    collector.onAccess(m_impl->corpusIds.at(node),
                       adjacency ? AccessKind::Adjacency : AccessKind::Vector, level, bytes);
  };
  try {
    auto result = searchStock(query, k);
    observer = {};
    return result;
  } catch (...) {
    observer = {};
    throw;
  }
}
void HnswAdapter::setEf(uint32_t ef) {
  if (!ef || !m_impl->index)
    throw std::invalid_argument("invalid ef or unbuilt index");
  m_impl->index->setEf(ef);
}
uint64_t HnswAdapter::nodeCount() const { return m_impl->adjacency.size(); }
uint32_t HnswAdapter::levelCount(uint64_t n) const { return m_impl->adjacency.at(n).size(); }
const std::vector<uint32_t> &HnswAdapter::neighbors(uint64_t n) const { return neighborsAt(n, 0); }
const std::vector<uint32_t> &HnswAdapter::neighborsAt(uint64_t n, uint32_t l) const {
  return m_impl->adjacency.at(n).at(l);
}
} // namespace pimann
