#ifndef PIMANN_LAYOUT_RANDOM_LAYOUT_H
#define PIMANN_LAYOUT_RANDOM_LAYOUT_H

#include <cstdint>
#include <string>
#include <vector>

#include "layout/memory_layout.h"

namespace pimann {

/// Seeded bijection used as a random-placement control.
class RandomLayout : public MemoryLayout {
public:
  explicit RandomLayout(uint64_t seed = 1) : m_seed(seed) {}

  std::string name() const override { return "random"; }
  void build(const GraphView &graph) override;
  uint64_t slotOf(uint64_t nodeId) const override;
  uint64_t nodeAt(uint64_t slot) const override;
  void exportMapping(const std::string &path) const override;

private:
  uint64_t m_seed;
  std::vector<uint64_t> m_nodeToSlot; ///< indexed by node id
  std::vector<uint64_t> m_slotToNode; ///< inverse
};

} // namespace pimann

#endif // PIMANN_LAYOUT_RANDOM_LAYOUT_H
