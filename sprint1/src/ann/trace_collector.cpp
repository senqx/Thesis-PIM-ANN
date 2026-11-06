#include "ann/trace_collector.h"

namespace pimann {

void TraceCollector::onAccess(
    uint64_t nodeId, AccessKind kind, uint32_t level, uint32_t byteSpan) {
  // A zero span means "a whole vector"; resolve it here so callers recording
  // vector reads don't repeat the dimension*dtype arithmetic.
  const uint32_t span =
      byteSpan != 0 ? byteSpan : m_dimension * m_dtypeBytes;
  m_trace.push_back(AccessRecord{
      m_currentQuery, nodeId, kind, level, span});
}

}  // namespace pimann
