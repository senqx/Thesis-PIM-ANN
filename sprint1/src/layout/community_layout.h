#ifndef PIMANN_LAYOUT_COMMUNITY_LAYOUT_H
#define PIMANN_LAYOUT_COMMUNITY_LAYOUT_H

#include <cstdint>
#include <string>
#include <vector>

#include "layout/memory_layout.h"

namespace pimann {

/// Asynchronous label propagation in seeded shuffled order, followed by
/// contiguous placement of the resulting groups. This lightweight structural
/// baseline is not an optimal graph partitioner.
class CommunityLayout : public MemoryLayout {
public:
  explicit CommunityLayout(uint32_t maxIterations = 20, uint64_t seed = 1)
      : m_maxIterations(maxIterations), m_seed(seed) {}

  std::string name() const override { return "community"; }
  void build(const GraphView &graph) override;
  uint64_t slotOf(uint64_t nodeId) const override;
  uint64_t nodeAt(uint64_t slot) const override;
  void exportMapping(const std::string &path) const override;

private:
  uint32_t m_maxIterations;
  uint64_t m_seed;
  std::vector<uint64_t> m_nodeToSlot;
  std::vector<uint64_t> m_slotToNode;
};

} // namespace pimann

#endif // PIMANN_LAYOUT_COMMUNITY_LAYOUT_H
