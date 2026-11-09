#include "layout_metrics.h"
#include <algorithm>
#include <stdexcept>
#include <unordered_map>
#include <unordered_set>
namespace pimann {
LayoutMetrics computeMetrics(const AccessTrace &trace, const MemoryLayout &layout,
                             uint32_t blockBytes, uint32_t vectorBytes) {
  if (!blockBytes || !vectorBytes)
    throw std::invalid_argument("zero metric size");
  LayoutMetrics m;
  uint64_t query = 0, prevNode = 0, prevBlock = 0, pairs = 0, samePairs = 0;
  bool haveQuery = false, haveVector = false;
  std::unordered_set<uint64_t> nodes;
  auto flush = [&] {
    std::unordered_map<uint64_t, uint64_t> counts;
    for (auto node : nodes)
      ++counts[layout.slotOf(node) * vectorBytes / blockBytes];
    pairs += nodes.size() * (nodes.size() ? nodes.size() - 1 : 0) / 2;
    for (auto [block, count] : counts) {
      (void)block;
      samePairs += count * (count - 1) / 2;
    }
    nodes.clear();
    haveVector = false;
  };
  for (const auto &r : trace) {
    if (!haveQuery || r.queryId != query) {
      flush();
      query = r.queryId;
      haveQuery = true;
    }
    if (r.kind != AccessKind::Vector)
      continue;
    const uint64_t block = layout.slotOf(r.nodeId) * vectorBytes / blockBytes;
    if (haveVector && r.nodeId != prevNode) {
      ++m.transitions;
      if (block == prevBlock)
        ++m.sameBlockTransitions;
    }
    nodes.insert(r.nodeId);
    prevNode = r.nodeId;
    prevBlock = block;
    haveVector = true;
  }
  flush();
  if (m.transitions)
    m.consecutiveVectorSameBlockPct = 100.0 * m.sameBlockTransitions / m.transitions;
  if (pairs)
    m.covisitSameBlockPct = 100.0 * samePairs / pairs;
  return m;
}
} // namespace pimann
