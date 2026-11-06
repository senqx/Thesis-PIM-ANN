#include "layout/community_layout.h"

#include <algorithm>
#include <fstream>
#include <numeric>
#include <random>
#include <stdexcept>
#include <unordered_map>
#include <vector>

#include "ann/graph_view.h"

namespace pimann {

void CommunityLayout::build(const GraphView& graph) {
  const uint64_t n = graph.nodeCount();

  // --- Label propagation -------------------------------------------------
  // Each node starts in its own community, then repeatedly adopts the label
  // most common among its neighbours. Nodes are updated in a shuffled order
  // each round to avoid oscillation; ties break toward the smaller label for
  // determinism. Converges when no label changes.
  std::vector<uint64_t> label(n);
  std::iota(label.begin(), label.end(), uint64_t{0});

  std::vector<uint64_t> order(n);
  std::iota(order.begin(), order.end(), uint64_t{0});
  std::mt19937_64 rng(m_seed);

  for (uint32_t iter = 0; iter < m_maxIterations; iter++) {
    std::shuffle(order.begin(), order.end(), rng);
    bool changed = false;
    for (const uint64_t node : order) {
      const std::vector<uint32_t>& adj = graph.neighbors(node);
      if (adj.empty()) {
        continue;
      }
      std::unordered_map<uint64_t, uint32_t> tally;
      for (const uint32_t neighbor : adj) {
        tally[label[neighbor]]++;
      }
      uint64_t best = label[node];
      uint32_t bestCount = 0;
      for (const auto& [lbl, count] : tally) {
        if (count > bestCount || (count == bestCount && lbl < best)) {
          best = lbl;
          bestCount = count;
        }
      }
      if (best != label[node]) {
        label[node] = best;
        changed = true;
      }
    }
    if (!changed) {
      break;
    }
  }

  // --- Place communities contiguously ------------------------------------
  // Group nodes by final label; order communities by descending size (large,
  // busy communities first) and nodes within a community by id for
  // determinism. This yields the slot assignment.
  std::unordered_map<uint64_t, std::vector<uint64_t>> groups;
  for (uint64_t node = 0; node < n; node++) {
    groups[label[node]].push_back(node);
  }
  std::vector<std::vector<uint64_t>> communities;
  communities.reserve(groups.size());
  for (auto& [lbl, members] : groups) {
    communities.push_back(std::move(members));
  }
  std::sort(
      communities.begin(), communities.end(),
      [](const std::vector<uint64_t>& a, const std::vector<uint64_t>& b) {
        return a.size() > b.size();
      });

  m_slotToNode.clear();
  m_slotToNode.reserve(n);
  for (std::vector<uint64_t>& members : communities) {
    std::sort(members.begin(), members.end());
    for (const uint64_t node : members) {
      m_slotToNode.push_back(node);
    }
  }

  m_nodeToSlot.resize(n);
  for (uint64_t slot = 0; slot < n; slot++) {
    m_nodeToSlot[m_slotToNode[slot]] = slot;
  }
}

uint64_t CommunityLayout::slotOf(uint64_t nodeId) const {
  return m_nodeToSlot[nodeId];
}

uint64_t CommunityLayout::nodeAt(uint64_t slot) const {
  return m_slotToNode[slot];
}

void CommunityLayout::exportMapping(const std::string& path) const {
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
