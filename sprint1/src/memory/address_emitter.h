#ifndef PIMANN_ADDRESS_EMITTER_H
#define PIMANN_ADDRESS_EMITTER_H
#include "ann/graph_view.h"
#include "memory/access_record.h"
#include <cstdint>
#include <ostream>
#include <vector>
namespace pimann {
class MemoryLayout;
// Dense vector payloads; each adjacency list has its own burst-aligned allocation.
// All graph levels are allocated in node/level order independently of vector layout.
struct AddressPlan {
  uint64_t vectorBase = 0x10000000;
  uint64_t adjacencyBase = 0;
  uint64_t vectorEnd = 0, adjacencyEnd = 0;
  uint32_t vectorBytes = 0, burst = 32;
  std::vector<std::vector<uint64_t>> adjacencyOffsets;
  std::vector<std::vector<uint32_t>> adjacencySpans;
  static AddressPlan forGraph(const GraphView &, uint32_t vectorBytes, uint32_t burst = 32);
};
class AddressEmitter {
public:
  AddressEmitter(const MemoryLayout &layout, const AddressPlan &plan)
      : m_layout(layout), m_plan(plan) {}
  uint64_t addressOf(const AccessRecord &) const;
  // LD address query_id kind; the thesis frontend preserves query boundaries.
  uint64_t emit(const AccessTrace &, std::ostream &) const;

private:
  const MemoryLayout &m_layout;
  const AddressPlan &m_plan;
};
} // namespace pimann
#endif
