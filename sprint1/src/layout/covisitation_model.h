#ifndef PIMANN_LAYOUT_COVISITATION_MODEL_H
#define PIMANN_LAYOUT_COVISITATION_MODEL_H

#include <cstdint>
#include <stdexcept>
#include <unordered_map>
#include <vector>

#include "memory/access_record.h"

namespace pimann {

/// Weighted pair count in the bounded within-query history.
struct CoVisit {
  uint32_t node;
  uint32_t weight;
};

/// Training-only temporal pair model. Each vector access contributes pairs with
/// the bounded list of recent distinct IDs. Repeated IDs do not refresh their
/// list position. Adjacency records and cross-query pairs are excluded.
class CoVisitationModel {
public:
  explicit CoVisitationModel(uint32_t window = 16) : m_window(window) {
    if (!window)
      throw std::invalid_argument("zero co-visit window");
  }
  /// Fold one trace into the model. May be called repeatedly (e.g. per query
  /// batch) before @ref finalize.
  void accumulate(const AccessTrace &trace);

  /// Freeze accumulation into compact per-node edge lists and the weight-ordered
  /// seed list. Call once after all @ref accumulate calls.
  void finalize();

  /// Co-visitation edges of @p node (empty if the node was never co-visited).
  const std::vector<CoVisit> &edges(uint64_t node) const;

  /// Nodes that have any co-visitation data, ordered by descending total
  /// weight — good starting points for a greedy grouping.
  const std::vector<uint64_t> &seedsByWeight() const { return m_seeds; }

private:
  uint32_t m_window;
  // Mutable accumulation stage, discarded after finalize().
  std::unordered_map<uint64_t, std::unordered_map<uint32_t, uint32_t>> m_build;
  // Finalised stage.
  std::unordered_map<uint64_t, std::vector<CoVisit>> m_edges;
  std::vector<uint64_t> m_seeds;
  std::vector<CoVisit> m_empty; ///< returned for unknown nodes
};

} // namespace pimann

#endif // PIMANN_LAYOUT_COVISITATION_MODEL_H
