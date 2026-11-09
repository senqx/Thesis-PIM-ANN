#include "layout/covisitation_model.h"

#include <algorithm>
#include <unordered_set>
#include <vector>

namespace pimann {

void CoVisitationModel::accumulate(const AccessTrace &trace) {
  // O(vector accesses * window) weighted history, reset for each query.
  const size_t window = m_window;

  uint64_t currentQuery = 0;
  bool haveQuery = false;
  std::vector<uint32_t> recent; // ring of the last `window` distinct nodes

  auto bump = [&](uint32_t a, uint32_t b) {
    if (a != b) {
      m_build[a][b]++;
      m_build[b][a]++;
    }
  };

  for (const AccessRecord &record : trace) {
    if (record.kind != AccessKind::Vector) {
      continue;
    }
    if (!haveQuery || record.queryId != currentQuery) {
      recent.clear();
      currentQuery = record.queryId;
      haveQuery = true;
    }
    const uint32_t node = static_cast<uint32_t>(record.nodeId);
    // Pair this access with the recent window (skip exact repeats already in
    // the window to keep weights meaningful).
    bool seen = false;
    for (const uint32_t prev : recent) {
      if (prev == node) {
        seen = true;
        continue;
      }
      bump(node, prev);
    }
    if (!seen) {
      recent.push_back(node);
      if (recent.size() > window) {
        recent.erase(recent.begin());
      }
    }
  }
}

void CoVisitationModel::finalize() {
  m_edges.reserve(m_build.size());
  m_seeds.reserve(m_build.size());
  std::unordered_map<uint64_t, uint64_t> totals;
  for (auto &[node, neighborMap] : m_build) {
    std::vector<CoVisit> list;
    list.reserve(neighborMap.size());
    uint64_t total = 0;
    for (const auto &[other, weight] : neighborMap) {
      list.push_back(CoVisit{other, weight});
      total += weight;
    }
    // Heaviest co-visited partner first, so grouping pulls in the strongest
    // ties before weaker ones.
    std::sort(list.begin(), list.end(), [](const CoVisit &a, const CoVisit &b) {
      return a.weight != b.weight ? a.weight > b.weight : a.node < b.node;
    });
    totals[node] = total;
    m_edges.emplace(node, std::move(list));
    m_seeds.push_back(node);
  }
  m_build.clear();

  // Seeds ordered by total co-visitation weight (descending): the busiest nodes
  std::sort(m_seeds.begin(), m_seeds.end(), [&totals](uint64_t a, uint64_t b) {
    const auto wa = totals.at(a), wb = totals.at(b);
    return wa != wb ? wa > wb : a < b;
  });
}

const std::vector<CoVisit> &CoVisitationModel::edges(uint64_t node) const {
  const auto it = m_edges.find(node);
  return it == m_edges.end() ? m_empty : it->second;
}

} // namespace pimann
