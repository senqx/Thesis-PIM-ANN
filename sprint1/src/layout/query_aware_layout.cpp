#include "layout/query_aware_layout.h"

#include <algorithm>
#include <fstream>
#include <queue>
#include <stdexcept>
#include <vector>

#include "ann/graph_view.h"

namespace pimann {

void QueryAwareLayout::build(const GraphView &graph) {
  const uint64_t n = graph.nodeCount();
  const uint32_t vectorBytes =
      m_vectorBytes ? m_vectorBytes : graph.dimension() * graph.dtypeBytes();
  if (!m_rowBytes || !vectorBytes)
    throw std::invalid_argument("zero layout size");
  m_slotToNode.clear();
  m_slotToNode.reserve(n);
  std::vector<bool> placed(n, false);

  auto place = [&](uint64_t node) {
    if (!placed[node]) {
      placed[node] = true;
      m_slotToNode.push_back(node);
    }
  };

  // Pass 1: greedy co-visitation grouping. Seeds are visited busiest-first; each
  // open block is filled with the seed's heaviest not-yet-placed partners, so a
  // block holds vectors that training queries wanted together.
  for (const uint64_t seed : m_model.seedsByWeight()) {
    if (seed >= n)
      throw std::invalid_argument("training node outside graph");
    if (placed[seed]) {
      continue;
    }
    place(seed);
    // Capacity is physical: a short previous group leaves a partial block.
    // Stop at this block's boundary, rather than letting the next seed spill.
    const uint64_t seedByte = (m_slotToNode.size() - 1) * vectorBytes;
    const uint64_t blockEnd = ((seedByte / m_rowBytes + 1) * m_rowBytes) / vectorBytes;
    for (const CoVisit &edge : m_model.edges(seed)) {
      if (m_slotToNode.size() >= blockEnd) {
        break;
      }
      if (edge.node >= n)
        throw std::invalid_argument("training partner outside graph");
      if (!placed[edge.node]) {
        place(edge.node);
      }
    }
  }

  // Pass 2: nodes with no training signal (or crowded out of a block) are
  // appended in BFS order, so untrained regions stay locally coherent rather
  // than scattered. Mirrors BfsLayout's component-restart handling.
  std::queue<uint64_t> frontier;
  for (uint64_t start = 0; start < n; start++) {
    if (placed[start]) {
      continue;
    }
    place(start);
    frontier.push(start);
    while (!frontier.empty()) {
      const uint64_t node = frontier.front();
      frontier.pop();
      for (const uint32_t neighbor : graph.neighbors(node)) {
        if (!placed[neighbor]) {
          place(neighbor);
          frontier.push(neighbor);
        }
      }
    }
  }

  m_nodeToSlot.resize(n);
  for (uint64_t slot = 0; slot < n; slot++) {
    m_nodeToSlot[m_slotToNode[slot]] = slot;
  }
}

uint64_t QueryAwareLayout::slotOf(uint64_t nodeId) const { return m_nodeToSlot.at(nodeId); }

uint64_t QueryAwareLayout::nodeAt(uint64_t slot) const { return m_slotToNode.at(slot); }

void QueryAwareLayout::exportMapping(const std::string &path) const {
  std::ofstream out(path);
  if (!out) {
    throw std::runtime_error("cannot open layout export: " + path);
  }
  out.exceptions(std::ios::badbit | std::ios::failbit);
  out << "logicalId,slot\n";
  for (uint64_t node = 0; node < m_nodeToSlot.size(); node++) {
    out << node << ',' << m_nodeToSlot[node] << '\n';
  }
  out.close();
}

} // namespace pimann
