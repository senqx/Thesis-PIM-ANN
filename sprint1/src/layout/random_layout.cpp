#include "layout/random_layout.h"

#include <algorithm>
#include <fstream>
#include <numeric>
#include <random>
#include <stdexcept>

#include "ann/graph_view.h"

namespace pimann {

void RandomLayout::build(const GraphView& graph) {
  const uint64_t n = graph.nodeCount();
  m_slotToNode.resize(n);
  std::iota(m_slotToNode.begin(), m_slotToNode.end(), uint64_t{0});

  std::mt19937_64 rng(m_seed);
  std::shuffle(m_slotToNode.begin(), m_slotToNode.end(), rng);

  m_nodeToSlot.resize(n);
  for (uint64_t slot = 0; slot < n; slot++) {
    m_nodeToSlot[m_slotToNode[slot]] = slot;
  }
}

uint64_t RandomLayout::slotOf(uint64_t nodeId) const {
  return m_nodeToSlot[nodeId];
}

uint64_t RandomLayout::nodeAt(uint64_t slot) const {
  return m_slotToNode[slot];
}

void RandomLayout::exportMapping(const std::string& path) const {
  std::ofstream out(path);
  if (!out) {
    throw std::runtime_error("cannot open layout export: " + path);
  }
  out << "logicalId,slot\n";
  for (uint64_t node = 0; node < m_nodeToSlot.size(); node++) {
    out << node << ',' << m_nodeToSlot[node] << '\n';
  }
}

}  // namespace pimann
