#ifndef PIMANN_LAYOUT_BFS_LAYOUT_H
#define PIMANN_LAYOUT_BFS_LAYOUT_H

#include <cstdint>
#include <string>
#include <vector>

#include "layout/memory_layout.h"

namespace pimann {

/// Breadth-first layout: assign slots in BFS visitation order of the base-layer
/// graph. Nodes close in graph hops end up close in memory, so a traversal that
/// hops between neighbours tends to stay within a DRAM row. This is the first
/// topology-aware baseline and the natural point of comparison for the proposed
/// method. Disconnected components are handled by restarting the BFS from the
/// lowest unvisited node id.
class BfsLayout : public MemoryLayout {
public:
  BfsLayout() = default;

  std::string name() const override { return "bfs"; }
  void build(const GraphView& graph) override;
  uint64_t slotOf(uint64_t nodeId) const override;
  uint64_t nodeAt(uint64_t slot) const override;
  void exportMapping(const std::string& path) const override;

private:
  std::vector<uint64_t> m_nodeToSlot;  ///< indexed by node id
  std::vector<uint64_t> m_slotToNode;  ///< inverse (BFS order)
};

}  // namespace pimann

#endif  // PIMANN_LAYOUT_BFS_LAYOUT_H
