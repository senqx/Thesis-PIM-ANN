#ifndef PIMANN_LAYOUT_METRICS_H
#define PIMANN_LAYOUT_METRICS_H

#include <cstdint>

#include "layout/memory_layout.h"
#include "memory/access_record.h"

namespace pimann {

/// Locality metrics for one layout over one trace. Separated so the
/// intra-vector bursts (always row-hits, independent of layout) never mask the
/// inter-vector transitions the layout actually controls.
struct LayoutMetrics {
  double allBurstRowHit = 0.0;    ///< every burst vs previous (proxy; misleads)
  double interVectorRowHit = 0.0; ///< only first-burst-of-vector transitions
  double covisitColocation = 0.0; ///< co-visited pairs sharing a row (held-out)
};

/// Compute all three metrics for @p layout over @p trace. @p rowBytes is the
/// DRAM row size; @p vectorBytes is one vector's size (dim*dtype).
///
/// The honest metric is @ref LayoutMetrics::interVectorRowHit: it asks, each
/// time the search moves from one vector to a *different* vector, whether the
/// new vector lives in the same DRAM row as the previous one. That is exactly
/// the transition a layout can turn from a row miss into a row hit. The
/// all-burst proxy is reported only to show how badly intra-vector bursts
/// inflate and flatten it.
LayoutMetrics computeMetrics(
    const AccessTrace& trace, const MemoryLayout& layout, uint32_t rowBytes,
    uint32_t vectorBytes);

}  // namespace pimann

#endif  // PIMANN_LAYOUT_METRICS_H
