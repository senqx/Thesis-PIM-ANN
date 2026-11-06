#ifndef PIMANN_LAYOUT_COVISITATION_MODEL_H
#define PIMANN_LAYOUT_COVISITATION_MODEL_H

#include <cstdint>
#include <unordered_map>
#include <vector>

#include "memory/access_record.h"

namespace pimann {

/// One co-visitation edge: how many training queries visited both this node and
/// some other node.
struct CoVisit {
  uint32_t node;
  uint32_t weight;
};

/// Empirical model of which nodes are read together, learned from a *training*
/// trace. For each query we take the set of distinct vector-accessed nodes and
/// increment a symmetric counter for every pair. The result is a weighted graph
/// whose edges say "these two vectors were wanted together this often" — the
/// signal a query-aware layout co-locates, and the thing static graph topology
/// (BFS) cannot see.
///
/// Built from training queries only; evaluation uses a disjoint test set, so a
/// measured locality gain reflects generalisation rather than fitting the very
/// queries being scored.
class CoVisitationModel {
public:
  /// Fold one trace into the model. May be called repeatedly (e.g. per query
  /// batch) before @ref finalize.
  void accumulate(const AccessTrace& trace);

  /// Freeze accumulation into compact per-node edge lists and the weight-ordered
  /// seed list. Call once after all @ref accumulate calls.
  void finalize();

  /// Co-visitation edges of @p node (empty if the node was never co-visited).
  const std::vector<CoVisit>& edges(uint64_t node) const;

  /// Nodes that have any co-visitation data, ordered by descending total
  /// weight — good starting points for a greedy grouping.
  const std::vector<uint64_t>& seedsByWeight() const { return m_seeds; }

private:
  // Mutable accumulation stage, discarded after finalize().
  std::unordered_map<uint64_t, std::unordered_map<uint32_t, uint32_t>> m_build;
  // Finalised stage.
  std::unordered_map<uint64_t, std::vector<CoVisit>> m_edges;
  std::vector<uint64_t> m_seeds;
  std::vector<CoVisit> m_empty;  ///< returned for unknown nodes
};

}  // namespace pimann

#endif  // PIMANN_LAYOUT_COVISITATION_MODEL_H
