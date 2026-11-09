#ifndef PIMANN_LAYOUT_BFS_LAYOUT_H
#define PIMANN_LAYOUT_BFS_LAYOUT_H

#include <cstdint>
#include <string>
#include <vector>

#include "layout/memory_layout.h"

namespace pimann {

/// Base-layer breadth-first ordering, restarting at the lowest unplaced ID.
/// This can improve colocation but does not guarantee same-row neighbours.
class BfsLayout : public MemoryLayout {
public:
  BfsLayout() = default;

  std::string name() const override { return "bfs"; }
  void build(const GraphView &graph) override;
  uint64_t slotOf(uint64_t nodeId) const override;
  uint64_t nodeAt(uint64_t slot) const override;
  void exportMapping(const std::string &path) const override;

private:
  std::vector<uint64_t> m_nodeToSlot; ///< indexed by node id
  std::vector<uint64_t> m_slotToNode; ///< inverse (BFS order)
};

} // namespace pimann

#endif // PIMANN_LAYOUT_BFS_LAYOUT_H
