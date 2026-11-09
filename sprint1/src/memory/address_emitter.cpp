#include "memory/address_emitter.h"
#include "layout/memory_layout.h"
#include <limits>
#include <stdexcept>
namespace pimann {
namespace {
uint64_t add(uint64_t a, uint64_t b) {
  if (a > UINT64_MAX - b)
    throw std::overflow_error("address overflow");
  return a + b;
}
uint64_t align(uint64_t a, uint32_t b) { return add(a, (b - a % b) % b); }
} // namespace
AddressPlan AddressPlan::forGraph(const GraphView &graph, uint32_t bytes, uint32_t burst) {
  if (!bytes || !burst || (burst & (burst - 1)))
    throw std::invalid_argument("invalid payload/burst");
  AddressPlan p;
  p.vectorBytes = bytes;
  p.burst = burst;
  const uint64_t n = graph.nodeCount();
  if (!n || n > (UINT64_MAX - p.vectorBase) / bytes)
    throw std::overflow_error("vector address space");
  p.vectorEnd = p.vectorBase + n * bytes;
  p.adjacencyBase = align(add(p.vectorEnd, 1024 * 1024), burst);
  uint64_t cursor = p.adjacencyBase;
  p.adjacencyOffsets.resize(n);
  p.adjacencySpans.resize(n);
  for (uint64_t node = 0; node < n; ++node) {
    for (uint32_t level = 0; level < graph.levelCount(node); ++level) {
      const uint64_t bytes = 4 + 4 * graph.neighborsAt(node, level).size();
      if (bytes > UINT32_MAX)
        throw std::overflow_error("adjacency size");
      p.adjacencyOffsets[node].push_back(cursor);
      p.adjacencySpans[node].push_back(bytes);
      cursor = align(add(cursor, bytes), burst);
    }
  }
  p.adjacencyEnd = cursor;
  return p;
}
uint64_t AddressEmitter::addressOf(const AccessRecord &r) const {
  if (r.nodeId >= m_plan.adjacencyOffsets.size())
    throw std::out_of_range("trace node");
  if (r.kind == AccessKind::Vector) {
    const auto slot = m_layout.slotOf(r.nodeId);
    if (slot >= m_plan.adjacencyOffsets.size())
      throw std::out_of_range("layout slot");
    return m_plan.vectorBase + slot * m_plan.vectorBytes;
  }
  if (r.kind == AccessKind::Adjacency) {
    if (r.byteSpan != m_plan.adjacencySpans.at(r.nodeId).at(r.level))
      throw std::invalid_argument("adjacency payload differs from allocation");
    return m_plan.adjacencyOffsets.at(r.nodeId).at(r.level);
  }
  throw std::invalid_argument("unmodelled access kind");
}
uint64_t AddressEmitter::emit(const AccessTrace &trace, std::ostream &out) const {
  uint64_t count = 0;
  for (const auto &r : trace) {
    const uint64_t addr = addressOf(r);
    const auto bytes = r.kind == AccessKind::Vector ? m_plan.vectorBytes : r.byteSpan;
    const uint64_t end = add(addr, bytes);
    for (uint64_t a = addr - addr % m_plan.burst; a < end; a = add(a, m_plan.burst)) {
      out << "LD 0x" << std::hex << a << std::dec << ' ' << r.queryId << ' '
          << (r.kind == AccessKind::Vector ? 'V' : 'A') << '\n';
      ++count;
    }
  }
  if (!out)
    throw std::runtime_error("trace output failed");
  return count;
}
} // namespace pimann
