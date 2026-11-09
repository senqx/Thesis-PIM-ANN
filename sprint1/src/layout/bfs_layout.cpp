#include "layout/bfs_layout.h"

#include <fstream>
#include <queue>
#include <stdexcept>
#include <vector>

#include "ann/graph_view.h"

namespace pimann {

void BfsLayout::build(const GraphView &graph) {
  const uint64_t n = graph.nodeCount();
  m_slotToNode.clear();
  m_slotToNode.reserve(n);

  std::vector<bool> visited(n, false);
  std::queue<uint64_t> frontier;

  // Restart from each lowest unvisited id so disconnected components (and any
  // unreachable nodes) still receive slots, in a deterministic order.
  for (uint64_t start = 0; start < n; start++) {
    if (visited[start]) {
      continue;
    }
    visited[start] = true;
    frontier.push(start);
    while (!frontier.empty()) {
      const uint64_t node = frontier.front();
      frontier.pop();
      m_slotToNode.push_back(node);
      for (const uint32_t neighbor : graph.neighbors(node)) {
        if (!visited[neighbor]) {
          visited[neighbor] = true;
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

uint64_t BfsLayout::slotOf(uint64_t nodeId) const { return m_nodeToSlot.at(nodeId); }

uint64_t BfsLayout::nodeAt(uint64_t slot) const { return m_slotToNode.at(slot); }

void BfsLayout::exportMapping(const std::string &path) const {
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
