#include "layout_metrics.h"

#include <algorithm>
#include <cstdint>
#include <vector>

namespace pimann {

namespace {

/// DRAM row index of a vector node under a layout. Vectors are packed by slot:
/// vectorBytes per slot, rowBytes per row.
uint64_t rowOf(
    const MemoryLayout& layout, uint64_t node, uint32_t rowBytes,
    uint32_t vectorBytes) {
  const uint64_t byteAddr = layout.slotOf(node) * vectorBytes;
  return byteAddr / rowBytes;
}

}  // namespace

LayoutMetrics computeMetrics(
    const AccessTrace& trace, const MemoryLayout& layout, uint32_t rowBytes,
    uint32_t vectorBytes) {
  LayoutMetrics out;
  const uint32_t burst = 64;
  const uint32_t burstsPerVector =
      std::max<uint32_t>(1, vectorBytes / burst);

  // --- all-burst proxy and inter-vector transitions ----------------------
  // Walk only Vector accesses in issue order. For each, the first burst is a
  // genuine inter-vector transition (compare its row to the previous vector's
  // row); the remaining bursts are intra-vector and always hit. We tally both
  // so the distortion is visible.
  uint64_t allHits = 0, allTotal = 0;
  uint64_t interHits = 0, interTotal = 0;
  bool have = false;
  uint64_t prevRow = 0;

  for (const AccessRecord& record : trace) {
    if (record.kind != AccessKind::Vector) {
      continue;
    }
    const uint64_t row = rowOf(layout, record.nodeId, rowBytes, vectorBytes);

    // First burst of this vector: the inter-vector transition.
    if (have) {
      if (row == prevRow) {
        interHits++;
        allHits++;
      }
      interTotal++;
      allTotal++;
    }
    // Remaining bursts are intra-vector: same row by construction.
    for (uint32_t b = 1; b < burstsPerVector; b++) {
      allHits++;
      allTotal++;
    }
    prevRow = row;
    have = true;
  }

  out.allBurstRowHit = allTotal > 0 ? 100.0 * allHits / allTotal : 0.0;
  out.interVectorRowHit = interTotal > 0 ? 100.0 * interHits / interTotal : 0.0;

  // --- co-visit colocation on held-out pairs -----------------------------
  const uint32_t blockSize =
      std::max<uint32_t>(1, rowBytes / std::max<uint32_t>(1, vectorBytes));
  uint64_t sameRow = 0, pairs = 0;
  uint64_t currentQuery = 0;
  bool haveQuery = false;
  std::vector<uint32_t> nodes;
  auto flush = [&]() {
    std::sort(nodes.begin(), nodes.end());
    nodes.erase(std::unique(nodes.begin(), nodes.end()), nodes.end());
    for (size_t i = 0; i < nodes.size(); i++) {
      for (size_t j = i + 1; j < nodes.size(); j++) {
        const uint64_t ri = layout.slotOf(nodes[i]) / blockSize;
        const uint64_t rj = layout.slotOf(nodes[j]) / blockSize;
        if (ri == rj) {
          sameRow++;
        }
        pairs++;
      }
    }
    nodes.clear();
  };
  for (const AccessRecord& record : trace) {
    if (record.kind != AccessKind::Vector) {
      continue;
    }
    if (!haveQuery || record.queryId != currentQuery) {
      flush();
      currentQuery = record.queryId;
      haveQuery = true;
    }
    nodes.push_back(static_cast<uint32_t>(record.nodeId));
  }
  flush();
  out.covisitColocation = pairs > 0 ? 100.0 * sameRow / pairs : 0.0;

  return out;
}

}  // namespace pimann
