#ifndef PIMANN_ANN_TRACE_COLLECTOR_H
#define PIMANN_ANN_TRACE_COLLECTOR_H

#include <cstdint>

#include "memory/access_record.h"

namespace pimann {

/// Collector for the selected vector/list demand accesses in stock search.
/// Prefetch, query-vector and scratch-memory traffic are outside this model.
class TraceCollector {
public:
  explicit TraceCollector(uint32_t dimension, uint32_t dtypeBytes)
      : m_dimension(dimension), m_dtypeBytes(dtypeBytes) {}

  /// Begin recording a new query; subsequent accesses are tagged with @p id.
  void beginQuery(uint64_t id) { m_currentQuery = id; }

  /// Record one access. @p byteSpan defaults to 0, meaning "a full vector"
  /// (dimension * dtypeBytes); callers pass an explicit span for adjacency or
  /// metadata reads whose size differs.
  void onAccess(uint64_t nodeId, AccessKind kind, uint32_t level, uint32_t byteSpan = 0);

  /// The accumulated trace across all queries, in issue order.
  const AccessTrace &trace() const { return m_trace; }

  /// Number of records recorded so far.
  uint64_t size() const { return m_trace.size(); }

private:
  AccessTrace m_trace;
  uint64_t m_currentQuery = 0;
  uint32_t m_dimension;
  uint32_t m_dtypeBytes;
};

} // namespace pimann

#endif // PIMANN_ANN_TRACE_COLLECTOR_H
