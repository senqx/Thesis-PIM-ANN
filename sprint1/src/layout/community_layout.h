#ifndef PIMANN_LAYOUT_COMMUNITY_LAYOUT_H
#define PIMANN_LAYOUT_COMMUNITY_LAYOUT_H

#include <cstdint>
#include <string>
#include <vector>

#include "layout/memory_layout.h"

namespace pimann {

/// Structural partitioning baseline: group nodes by graph community, then place
/// each community's members contiguously. Communities are found with
/// synchronous label propagation (each node adopts the most common label among
/// its neighbours, iterated to convergence) -- a dependency-free stand-in for
/// METIS/Louvain that needs only the graph topology and a C++ compiler.
///
/// This is the strong structural baseline the proposed query-aware layout must
/// beat: it co-locates nodes that are *structurally* close, whereas query-aware
/// co-locates nodes that are *actually read together*. The gap between them
/// isolates the value of the workload signal.
class CommunityLayout : public MemoryLayout {
public:
  explicit CommunityLayout(uint32_t maxIterations = 20, uint64_t seed = 1)
      : m_maxIterations(maxIterations), m_seed(seed) {}

  std::string name() const override { return "community"; }
  void build(const GraphView& graph) override;
  uint64_t slotOf(uint64_t nodeId) const override;
  uint64_t nodeAt(uint64_t slot) const override;
  void exportMapping(const std::string& path) const override;

private:
  uint32_t m_maxIterations;
  uint64_t m_seed;
  std::vector<uint64_t> m_nodeToSlot;
  std::vector<uint64_t> m_slotToNode;
};

}  // namespace pimann

#endif  // PIMANN_LAYOUT_COMMUNITY_LAYOUT_H
