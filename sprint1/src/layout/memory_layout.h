#ifndef PIMANN_LAYOUT_MEMORY_LAYOUT_H
#define PIMANN_LAYOUT_MEMORY_LAYOUT_H

#include <cstdint>
#include <string>

namespace pimann {

class GraphView;

/// Strategy that assigns each logical HNSW node a physical *slot* (a position
/// in the contiguous vector-storage array). Changing the slot assignment is the
/// one lever a memory controller cannot pull for us, and is the subject of the
/// thesis: co-locating co-visited nodes into the same DRAM rows.
///
/// A layout maps logical node ids to a dense slot range [0, nodeCount); the
/// AddressEmitter later turns a slot into a byte address. Implementations must
/// produce a bijection so logical graph correctness is preserved.
class MemoryLayout {
public:
  virtual ~MemoryLayout() = default;

  /// Human-readable strategy name, used in result filenames and reports
  /// (e.g. "random", "bfs", "metis").
  virtual std::string name() const = 0;

  /// Compute the slot assignment from the graph topology. Called once before
  /// any mapping query. May be expensive (that cost is itself a measured
  /// quantity in the overhead phase).
  virtual void build(const GraphView& graph) = 0;

  /// Logical node id -> physical slot. Must be defined for every node after
  /// @ref build and form a bijection over [0, nodeCount).
  virtual uint64_t slotOf(uint64_t nodeId) const = 0;

  /// Physical slot -> logical node id (inverse of @ref slotOf). Needed to
  /// reason about which nodes share a DRAM row.
  virtual uint64_t nodeAt(uint64_t slot) const = 0;

  /// Persist the mapping (one "logicalId,slot" pair per line) so an experiment
  /// is reproducible without rebuilding the layout.
  virtual void exportMapping(const std::string& path) const = 0;
};

}  // namespace pimann

#endif  // PIMANN_LAYOUT_MEMORY_LAYOUT_H
