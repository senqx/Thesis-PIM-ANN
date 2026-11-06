#ifndef PIMANN_MEMORY_ACCESS_RECORD_H
#define PIMANN_MEMORY_ACCESS_RECORD_H

#include <cstdint>
#include <vector>

namespace pimann {

/// Which logical structure an access touches. Keeping vector-data reads
/// separate from adjacency-list reads is the whole point of the trace
/// collector: the two have very different locality and the layout work targets
/// them differently.
enum class AccessKind {
  Vector,     ///< a stored feature vector (the big, dim*dtype payload)
  Adjacency,  ///< a node's neighbour list (graph edges)
  Metadata,   ///< per-node metadata (level, flags)
  Candidate   ///< search-time scratch structures (priority queue, visited set)
};

/// One logical memory access, recorded during a real HNSW search and
/// independent of any physical layout. The @ref nodeId is a *logical* graph
/// node; translation to a byte address is deferred to a MemoryLayout plus an
/// AddressEmitter, so the same trace can be replayed under any layout.
struct AccessRecord {
  uint64_t queryId;   ///< which query produced this access
  uint64_t nodeId;    ///< logical HNSW node id touched
  AccessKind kind;    ///< what structure was read
  uint32_t level;     ///< HNSW layer the access occurred on (0 = base)
  uint32_t byteSpan;  ///< bytes this record represents (one payload, pre-burst)
};

/// A full trace is just an ordered list of records. Order is the access order
/// of the real search and must be preserved; the layout changes *addresses*,
/// never the order.
using AccessTrace = std::vector<AccessRecord>;

}  // namespace pimann

#endif  // PIMANN_MEMORY_ACCESS_RECORD_H
