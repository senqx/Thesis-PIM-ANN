#ifndef PIMANN_LAYOUT_QUERY_AWARE_LAYOUT_H
#define PIMANN_LAYOUT_QUERY_AWARE_LAYOUT_H

#include <cstdint>
#include <string>
#include <vector>

#include "layout/covisitation_model.h"
#include "layout/memory_layout.h"

namespace pimann {

/// Greedy placement using training co-visitation weights. Each seed's partners
/// fill only the remaining capacity of the current address block. The block is
/// a heuristic parameter; the simulator's actual mapping is checked separately.
/// Nodes not placed from training are appended through BFS restarts.
class QueryAwareLayout : public MemoryLayout {
public:
  /// @p model is the co-visitation signal learned from TRAINING queries only.
  /// @p rowBytes is the target address-block size.
  QueryAwareLayout(const CoVisitationModel &model, uint32_t rowBytes = 1024,
                   uint32_t vectorBytes = 0)
      : m_model(model), m_rowBytes(rowBytes), m_vectorBytes(vectorBytes) {}

  std::string name() const override { return "query_aware"; }
  void build(const GraphView &graph) override;
  uint64_t slotOf(uint64_t nodeId) const override;
  uint64_t nodeAt(uint64_t slot) const override;
  void exportMapping(const std::string &path) const override;

private:
  const CoVisitationModel &m_model;
  uint32_t m_rowBytes;
  uint32_t m_vectorBytes;
  std::vector<uint64_t> m_nodeToSlot;
  std::vector<uint64_t> m_slotToNode;
};

} // namespace pimann

#endif // PIMANN_LAYOUT_QUERY_AWARE_LAYOUT_H
