#include "layout/covisitation_model.h"

#include <algorithm>
#include <unordered_set>
#include <vector>

namespace pimann {

void CoVisitationModel::accumulate(const AccessTrace& trace) {
  // Count co-visitation between nodes accessed close together *in time* within a
  // query, using a sliding window over the issue-ordered vector accesses. Two
  // reasons this beats all-pairs: (1) temporally adjacent accesses are what
  // actually compete for the row buffer, so the signal is more faithful; (2) it
  // is O(accesses * window) instead of O(visited^2), which matters at SIFT1M
  // scale where a query can touch thousands of nodes. The window is the only
  // tuning knob and defaults to a few DRAM rows' worth of accesses.
  constexpr size_t window = 16;

  uint64_t currentQuery = 0;
  bool haveQuery = false;
  std::vector<uint32_t> recent;  // ring of the last `window` distinct nodes

  auto bump = [&](uint32_t a, uint32_t b) {
    if (a != b) {
      m_build[a][b]++;
      m_build[b][a]++;
    }
  };

  for (const AccessRecord& record : trace) {
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
  for (auto& [node, neighborMap] : m_build) {
    std::vector<CoVisit> list;
    list.reserve(neighborMap.size());
    uint64_t total = 0;
    for (const auto& [other, weight] : neighborMap) {
      list.push_back(CoVisit{other, weight});
      total += weight;
    }
    // Heaviest co-visited partner first, so grouping pulls in the strongest
    // ties before weaker ones.
    std::sort(
        list.begin(), list.end(),
        [](const CoVisit& a, const CoVisit& b) {
          return a.weight > b.weight;
        });
    m_edges.emplace(node, std::move(list));
    m_seeds.push_back(node);
  }
  m_build.clear();

  // Seeds ordered by total co-visitation weight (descending): the busiest nodes
  std::sort(
      m_seeds.begin(), m_seeds.end(),
      [this](uint64_t a, uint64_t b) {
        uint64_t wa = 0;
        for (const CoVisit& e : m_edges[a]) {
          wa += e.weight;
        }
        uint64_t wb = 0;
        for (const CoVisit& e : m_edges[b]) {
          wb += e.weight;
        }
        return wa > wb;
      });
}

const std::vector<CoVisit>& CoVisitationModel::edges(uint64_t node) const {
  const auto it = m_edges.find(node);
  return it == m_edges.end() ? m_empty : it->second;
}

}  // namespace pimann
