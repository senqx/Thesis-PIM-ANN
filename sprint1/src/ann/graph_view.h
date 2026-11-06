#ifndef PIMANN_ANN_GRAPH_VIEW_H
#define PIMANN_ANN_GRAPH_VIEW_H

#include <cstdint>
#include <vector>

namespace pimann {

/// Read-only, implementation-agnostic view of an HNSW graph's topology.
///
/// Layout strategies (BFS, METIS, community, ...) need to walk the graph but
/// must not depend on hnswlib's internals. The HnswAdapter builds one of these
/// once; every MemoryLayout consumes it. Only base-layer (level 0) connectivity
/// is exposed here, because that layer holds every node and dominates both the
/// memory footprint and the search traffic.
class GraphView {
public:
  virtual ~GraphView() = default;

  /// Total number of nodes (level-0 size).
  virtual uint64_t nodeCount() const = 0;

  /// Base-layer neighbours of @p nodeId. Returned by const reference to avoid
  /// copying adjacency lists during a full-graph traversal.
  virtual const std::vector<uint32_t>& neighbors(
      uint64_t nodeId) const = 0;

  /// Dimensionality of the stored vectors (needed to size byte spans).
  virtual uint32_t dimension() const = 0;

  /// Bytes per vector component (e.g. 4 for float32, 1 for int8).
  virtual uint32_t dtypeBytes() const = 0;
};

}  // namespace pimann

#endif  // PIMANN_ANN_GRAPH_VIEW_H
