#ifndef PIMANN_LAYOUT_METRICS_H
#define PIMANN_LAYOUT_METRICS_H
#include "layout/memory_layout.h"
#include "memory/access_record.h"
namespace pimann {
// Within-query address statistics only. These do not model DRAM banks or scheduling.
struct LayoutMetrics {
  double consecutiveVectorSameBlockPct = 0;
  double covisitSameBlockPct = 0;
  uint64_t transitions = 0, sameBlockTransitions = 0;
};
LayoutMetrics computeMetrics(const AccessTrace &, const MemoryLayout &, uint32_t blockBytes,
                             uint32_t vectorBytes);
} // namespace pimann
#endif
