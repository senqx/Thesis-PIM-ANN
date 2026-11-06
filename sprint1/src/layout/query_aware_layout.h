#ifndef PIMANN_LAYOUT_QUERY_AWARE_LAYOUT_H
#define PIMANN_LAYOUT_QUERY_AWARE_LAYOUT_H

#include <cstdint>
#include <string>
#include <vector>

#include "layout/covisitation_model.h"
#include "layout/memory_layout.h"

namespace pimann {

/// The proposed contribution: place vectors so that nodes empirically read
/// together (from a training trace) share a DRAM row. Unlike BFS, which follows
/// static graph topology, this follows the *observed query workload* — the
/// signal that actually drives row-buffer locality.
///
/// Build is a greedy grouping. Working from the busiest co-visited node
/// outward, it fills fixed-size blocks (one DRAM row's worth of vectors, per the
/// byte-budget rule C* = rowBytes / vectorBytes) with a seed's heaviest
/// co-visited partners. Nodes with no training signal are appended in BFS order
/// so every node still gets a slot and disconnected regions stay locally
/// coherent.
class QueryAwareLayout : public MemoryLayout {
public:
  /// @p model is the co-visitation signal learned from TRAINING queries only.
  /// @p rowBytes is the DRAM row size the block target is derived from.
  QueryAwareLayout(const CoVisitationModel& model, uint32_t rowBytes = 2048)
      : m_model(model), m_rowBytes(rowBytes) {}

  std::string name() const override { return "query_aware"; }
  void build(const GraphView& graph) override;
  uint64_t slotOf(uint64_t nodeId) const override;
  uint64_t nodeAt(uint64_t slot) const override;
  void exportMapping(const std::string& path) const override;

private:
  const CoVisitationModel& m_model;
  uint32_t m_rowBytes;
  std::vector<uint64_t> m_nodeToSlot;
  std::vector<uint64_t> m_slotToNode;
};

}  // namespace pimann

#endif  // PIMANN_LAYOUT_QUERY_AWARE_LAYOUT_H
